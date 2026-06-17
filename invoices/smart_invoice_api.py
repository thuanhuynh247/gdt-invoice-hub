"""Smart Invoice API endpoints matching smart-invoice.vn specification.

Provides three stateless REST endpoints compatible with the smart-invoice.vn
client specification:
  - POST /API/login          — Two-phase captcha+login flow
  - POST /API/get_purchase/<mst>       — Purchase invoice headers
  - POST /API/get_purchase_items/<mst> — Purchase invoice line-item rows

These endpoints are session-free (no Flask session cookies) and authenticate
via a ``token`` header or ``Authorization: Bearer <token>`` header to support
external tool integrations (Postman, automation scripts, etc.).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, jsonify, request, current_app, Response

from auth.captcha import fetch_captcha_payload
from auth.service import authenticate_user, AuthenticationError
from invoices.service import fetch_invoices, fetch_invoice_line_items, InvoiceQuery

logger = logging.getLogger(__name__)

smart_invoice_blueprint = Blueprint("smart_invoice_api", __name__)

# ---------------------------------------------------------------------------
# Thread-safe captcha cache with TTL (120 seconds) and bounded size (50 entries)
# ---------------------------------------------------------------------------
_CAPTCHA_CACHE: dict[str, dict] = {}
_CAPTCHA_LOCK = threading.Lock()
_CAPTCHA_MAX_SIZE = 50
_CAPTCHA_TTL_SECONDS = 120


def _cache_put(key: str, cookies: dict, svg: str = "") -> None:
    """Store captcha cookies and SVG content keyed by generated UUID, with TTL and eviction."""
    now = time.monotonic()
    with _CAPTCHA_LOCK:
        # Evict expired entries
        expired = [k for k, v in _CAPTCHA_CACHE.items()
                    if now - v["_ts"] > _CAPTCHA_TTL_SECONDS]
        for k in expired:
            _CAPTCHA_CACHE.pop(k, None)
        # Evict oldest if over limit
        while len(_CAPTCHA_CACHE) >= _CAPTCHA_MAX_SIZE:
            oldest_key = min(_CAPTCHA_CACHE, key=lambda k: _CAPTCHA_CACHE[k]["_ts"])
            _CAPTCHA_CACHE.pop(oldest_key, None)
        _CAPTCHA_CACHE[key] = {"cookies": cookies, "svg": svg, "_ts": now}


def _cache_pop(key: str) -> dict:
    """Pop entry for a captcha key (one-time use). Returns empty dict if missing/expired."""
    now = time.monotonic()
    with _CAPTCHA_LOCK:
        entry = _CAPTCHA_CACHE.pop(key, None)
    if not entry:
        return {}
    if now - entry["_ts"] > _CAPTCHA_TTL_SECONDS:
        return {}  # Expired
    return entry


# ---------------------------------------------------------------------------
# Helper: parse dd/mm/yyyy dates
# ---------------------------------------------------------------------------
def _parse_date(date_str: str) -> datetime.date:
    """Parse date from dd/mm/yyyy format, raising ValueError on bad input."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        raise ValueError(f"Ngay khong dung dinh dang dd/mm/yyyy: {date_str}")


# ---------------------------------------------------------------------------
# Helper: extract token from request headers
# ---------------------------------------------------------------------------
def _extract_token() -> str | None:
    """Read authentication token from ``token`` header or ``Authorization: Bearer``."""
    token = request.headers.get("token")
    if token:
        return token.strip()
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def _require_token(fn):
    """Decorator that rejects requests without a valid token header."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Chua cung cap token xac thuc."}), 401
        # Inject token into kwargs for the wrapped handler
        kwargs["_token"] = token
        return fn(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Helper: extract and validate date range from JSON payload
# ---------------------------------------------------------------------------
def _extract_date_range():
    """Parse ``fromdate`` / ``todate`` from JSON body.  Returns (date_from, date_to, nbmst, error_response)."""
    payload = request.get_json(silent=True) or {}
    fromdate_str = payload.get("fromdate")
    todate_str = payload.get("todate")
    nbmst = payload.get("nbmst", "").strip()

    if not fromdate_str or not todate_str:
        return None, None, None, (jsonify({"error": "Thieu tham so fromdate hoac todate."}), 400)
    try:
        date_from = _parse_date(fromdate_str)
        date_to = _parse_date(todate_str)
    except ValueError as e:
        return None, None, None, (jsonify({"error": str(e)}), 400)

    return date_from, date_to, nbmst, None


# ===========================================================================
# POST /API/login
# ===========================================================================
@smart_invoice_blueprint.post("/API/login")
def api_login():
    """Smart-invoice compatible login endpoint (two-phase captcha flow).

    Phase 1 — If ``captcha`` or ``key`` is empty/missing:
        Returns ``{"content": "<svg ...>", "key": "..."}`` with the captcha image.

    Phase 2 — If ``captcha`` and ``key`` are provided:
        Validates credentials with GDT and returns the raw JWT/session token
        as ``text/plain``.
    """
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    captcha = payload.get("captcha", "").strip()
    captcha_key = payload.get("key", "").strip()

    # ── Phase 1: Return captcha ────────────────────────────────────────
    if not captcha or not captcha_key:
        try:
            captcha_payload = fetch_captcha_payload()
            key = captcha_payload.get("key") or str(uuid.uuid4())
            content = captcha_payload["content"]
            cookies = captcha_payload.get("cookies", {})

            _cache_put(key, cookies, content)

            return jsonify({"content": content, "key": key})
        except Exception as e:
            logger.error("Error fetching captcha for smart-invoice login: %s", e)
            return jsonify({"error": f"Khong the lay captcha tu GDT: {e}"}), 500

    # ── Phase 2: Authenticate ──────────────────────────────────────────
    entry = _cache_pop(captcha_key)
    cookies = entry.get("cookies", {})
    svg_content = entry.get("svg", "")

    if captcha.upper() == "AUTO":
        if svg_content:
            try:
                from auth.captcha_solver import solve_captcha_from_svg
                captcha = solve_captcha_from_svg(svg_content, captcha_key=captcha_key)
                logger.info("Auto-solved captcha for smart-invoice login: %s", captcha)
            except Exception as e:
                logger.error("Failed to auto-solve captcha: %s", e)
                return jsonify({"error": f"Khong the tu dong giai captcha: {e}"}), 400
        else:
            return jsonify({"error": "Khong co du lieu SVG de tu dong giai captcha hoac captcha da het han."}), 400

    try:
        auth_data = authenticate_user(
            username=username,
            password=password,
            captcha=captcha,
            captcha_key=captcha_key,
            captcha_cookies=cookies,
        )

        # Prefer JWT; fall back to session_token (mock mode returns jwt=None)
        token = auth_data.get("jwt") or auth_data.get("session_token")
        if not token:
            return jsonify({"error": "Dang nhap thanh cong nhung khong nhan duoc token."}), 401

        # Return raw token as plain text per smart-invoice.vn specification
        return Response(token, mimetype="text/plain")
    except AuthenticationError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logger.error("Unexpected error in smart-invoice login: %s", e)
        return jsonify({"error": f"Loi he thong: {e}"}), 500


# ===========================================================================
# POST /API/get_purchase/<mst>
# ===========================================================================
@smart_invoice_blueprint.post("/API/get_purchase/<mst>")
@_require_token
def get_purchase(mst: str, *, _token: str = ""):
    """Return purchase invoice headers in smart-invoice.vn JSON format."""
    date_from, date_to, nbmst_filter, err = _extract_date_range()
    if err:
        return err

    # Temporarily inject token so fetch_invoices can use it for live GDT calls
    original_jwt = current_app.config.get("CURRENT_JWT")
    current_app.config["CURRENT_JWT"] = _token

    try:
        query = InvoiceQuery(date_from=date_from, date_to=date_to, direction="purchase")
        invoices = fetch_invoices(query)

        mapped = []
        for inv in invoices:
            raw = inv.get("raw") or {}

            # Apply optional supplier MST filter (nbmst)
            inv_nbmst = raw.get("nbmst") or ""
            if nbmst_filter and nbmst_filter not in inv_nbmst:
                continue

            mapped.append({
                "khmshdon": raw.get("khmshdon") or "1",
                "khhdon":   raw.get("khhdon") or inv.get("description") or "",
                "shdon":    raw.get("shdon") or inv["id"].split("-")[-1],
                "ntao":     raw.get("ntao") or raw.get("tdlap") or (inv["date"] + "T00:00:00.000Z"),
                "nbten":    raw.get("nbten") or inv.get("issuer") or "",
                "nbmst":    inv_nbmst or mst,
                "nbdchi":   raw.get("nbdchi") or "",
                "tgtcthue": str(raw.get("tgtcthue") or inv.get("amount") or 0),
                "tgtthue":  str(raw.get("tgtthue") or 0),
                "tgtttbso": str(raw.get("tgtttbso") or inv.get("amount") or 0),
                "dvtte":    raw.get("dvtte") or "VND",
                "cqt":      raw.get("cqt") or "",
                "tchat":    raw.get("tchat") or "1",
                "tthai":    raw.get("tthai") or inv.get("status") or "",
                "ttxly":    raw.get("ttxly") or "",
            })

        return jsonify(mapped)
    except Exception as e:
        logger.error("Error fetching purchase invoices for smart-invoice API: %s", e)
        return jsonify({"error": f"Loi truy van hoa don: {e}"}), 500
    finally:
        if original_jwt is not None:
            current_app.config["CURRENT_JWT"] = original_jwt
        else:
            current_app.config.pop("CURRENT_JWT", None)


# ===========================================================================
# POST /API/get_purchase_items/<mst>
# ===========================================================================
@smart_invoice_blueprint.post("/API/get_purchase_items/<mst>")
@_require_token
def get_purchase_items(mst: str, *, _token: str = ""):
    """Return detailed item rows for all purchase invoices in the date range."""
    date_from, date_to, nbmst_filter, err = _extract_date_range()
    if err:
        return err

    original_jwt = current_app.config.get("CURRENT_JWT")
    current_app.config["CURRENT_JWT"] = _token

    try:
        query = InvoiceQuery(date_from=date_from, date_to=date_to, direction="purchase")
        invoices = fetch_invoices(query)

        all_items = []
        stt = 1

        for inv in invoices:
            raw = inv.get("raw") or {}
            inv_nbmst = raw.get("nbmst") or ""
            if nbmst_filter and nbmst_filter not in inv_nbmst:
                continue

            try:
                line_items = fetch_invoice_line_items(inv["id"])
            except Exception as item_err:
                logger.warning("Could not load line items for invoice %s: %s", inv["id"], item_err)
                continue

            for item in line_items:
                all_items.append({
                    "STT":      stt,
                    "TChat":    "1",
                    "MHHDVu":   item.get("id") or "",
                    "THHDVu":   item.get("item_name") or "",
                    "DVTinh":   item.get("unit") or "",
                    "SLuong":   item.get("quantity") or 0.0,
                    "DGia":     item.get("unit_price") or 0.0,
                    "ThTien":   item.get("amount_before_tax") or 0.0,
                    "TSuat":    item.get("tax_rate") or "10%",
                    "TLCKhau":  0.0,
                    "STCKhau":  0.0,
                })
                stt += 1

        return jsonify(all_items)
    except Exception as e:
        logger.error("Error fetching purchase items for smart-invoice API: %s", e)
        return jsonify({"error": f"Loi truy van chi tiet mat hang: {e}"}), 500
    finally:
        if original_jwt is not None:
            current_app.config["CURRENT_JWT"] = original_jwt
        else:
            current_app.config.pop("CURRENT_JWT", None)
