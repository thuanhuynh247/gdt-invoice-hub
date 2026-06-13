"""Smart Invoice API endpoints matching smart-invoice.vn specification."""

from __future__ import annotations

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, Response

from auth.captcha import fetch_captcha_payload
from auth.service import authenticate_user, AuthenticationError
from invoices.service import fetch_invoices, fetch_invoice_line_items, InvoiceQuery

logger = logging.getLogger(__name__)

smart_invoice_blueprint = Blueprint("smart_invoice_api", __name__)

# Cache to store captcha keys and their corresponding cookies for stateless/cookie-less login
API_CAPTCHA_CACHE = {}


def parse_date(date_str: str) -> datetime.date:
    """Parse date from dd/mm/yyyy format."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except Exception as e:
        raise ValueError(f"Ngay khong dung dinh dang dd/mm/yyyy: {date_str}")


@smart_invoice_blueprint.post("/API/login")
@smart_invoice_blueprint.post("/api/login")
def api_login():
    """Smart-invoice compatible login endpoint.
    
    If captcha is empty, returns the captcha content and key.
    If captcha and key are provided, validates with GDT and returns the token.
    """
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    captcha = payload.get("captcha", "").strip()
    captcha_key = payload.get("key", "").strip()

    # Case 1: Captcha is empty -> Fetch and return new captcha
    if not captcha or not captcha_key:
        try:
            captcha_payload = fetch_captcha_payload()
            key = captcha_payload["key"]
            content = captcha_payload["content"]
            cookies = captcha_payload.get("cookies", {})
            
            # Store in cache
            API_CAPTCHA_CACHE[key] = cookies
            
            return jsonify({
                "content": content,
                "key": key
            })
        except Exception as e:
            logger.error(f"Error fetching captcha for smart-invoice login: {e}")
            return jsonify({"error": f"Khong the lay captcha tu GDT: {str(e)}"}), 500

    # Case 2: Validate captcha & credentials
    cookies = API_CAPTCHA_CACHE.pop(captcha_key, {})
    try:
        auth_data = authenticate_user(
            username=username,
            password=password,
            captcha=captcha,
            captcha_key=captcha_key,
            captcha_cookies=cookies
        )
        
        token = auth_data.get("jwt") or auth_data.get("session_token")
        if not token:
            return jsonify({"error": "Dang nhap thanh cong nhung khong nhan duoc JWT."}), 401
            
        # Return raw JWT token directly as requested by the spec
        return Response(token, mimetype="text/plain")
    except AuthenticationError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logger.error(f"Unexpected error in smart-invoice login: {e}")
        return jsonify({"error": f"Loi he thong: {str(e)}"}), 500


@smart_invoice_blueprint.post("/API/get_purchase/<mst>")
@smart_invoice_blueprint.post("/api/get_purchase/<mst>")
def get_purchase(mst):
    """Retrieve purchase invoices in smart-invoice format."""
    # Authenticate token from header
    token = request.headers.get("token") or request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]
        
    if not token:
        return jsonify({"error": "Chua cung cap token xac thuc."}), 401

    payload = request.get_json(silent=True) or {}
    fromdate_str = payload.get("fromdate")
    todate_str = payload.get("todate")

    if not fromdate_str or not todate_str:
        return jsonify({"error": "Thieu tham so fromdate hoac todate."}), 400

    try:
        date_from = parse_date(fromdate_str)
        date_to = parse_date(todate_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Put token in configuration context so fetch_invoices can utilize it
    original_jwt = current_app.config.get("CURRENT_JWT")
    current_app.config["CURRENT_JWT"] = token
    
    try:
        query = InvoiceQuery(date_from=date_from, date_to=date_to, direction="purchase")
        invoices = fetch_invoices(query)
        
        # Map to smart-invoice format
        mapped_invoices = []
        for inv in invoices:
            raw = inv.get("raw") or {}
            mapped_invoices.append({
                "khmshdon": raw.get("khmshdon") or "1",
                "khhdon": raw.get("khhdon") or inv.get("description") or "K23DAD",
                "shdon": raw.get("shdon") or inv["id"].split("-")[-1],
                "ntao": raw.get("ntao") or raw.get("tdlap") or (inv["date"] + "T00:00:00.000Z"),
                "nbten": raw.get("nbten") or inv["issuer"],
                "nbmst": raw.get("nbmst") or "0316459946",
                "nbdchi": raw.get("nbdchi"),
                "tgtcthue": str(raw.get("tgtcthue") or inv["amount"]),
                "tgtthue": str(raw.get("tgtthue") or "0"),
                "tgtttbso": str(raw.get("tgtttbso") or inv["amount"]),
                "dvtte": raw.get("dvtte") or "VND",
                "cqt": raw.get("cqt") or "7901",
                "tchat": raw.get("tchat") or "1",
                "tthai": raw.get("tthai") or inv["status"],
                "ttxly": raw.get("ttxly") or "Đã xử lý"
            })
            
        return jsonify(mapped_invoices)
    except Exception as e:
        logger.error(f"Error fetching purchase invoices for smart-invoice API: {e}")
        return jsonify({"error": f"Loi truy van hoa don: {str(e)}"}), 500
    finally:
        # Restore configuration JWT
        current_app.config["CURRENT_JWT"] = original_jwt


@smart_invoice_blueprint.post("/API/get_purchase_items/<mst>")
@smart_invoice_blueprint.post("/api/get_purchase_items/<mst>")
def get_purchase_items(mst):
    """Retrieve detailed item rows for all purchase invoices in date range."""
    # Authenticate token from header
    token = request.headers.get("token") or request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]
        
    if not token:
        return jsonify({"error": "Chua cung cap token xac thuc."}), 401

    payload = request.get_json(silent=True) or {}
    fromdate_str = payload.get("fromdate")
    todate_str = payload.get("todate")

    if not fromdate_str or not todate_str:
        return jsonify({"error": "Thieu tham so fromdate hoac todate."}), 400

    try:
        date_from = parse_date(fromdate_str)
        date_to = parse_date(todate_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Put token in configuration context so fetch_invoices can utilize it
    original_jwt = current_app.config.get("CURRENT_JWT")
    current_app.config["CURRENT_JWT"] = token
    
    try:
        query = InvoiceQuery(date_from=date_from, date_to=date_to, direction="purchase")
        invoices = fetch_invoices(query)
        
        all_items = []
        stt_counter = 1
        
        for inv in invoices:
            try:
                line_items = fetch_invoice_line_items(inv["id"])
                for item in line_items:
                    # Map GDT line item fields to smart-invoice items format
                    # STT, TChat, MHHDVu, THHDVu, DVTinh, SLuong, DGia, ThTien, TSuat, TLCKhau, STCKhau
                    all_items.append({
                        "STT": stt_counter,
                        "TChat": "1",  # 1 for normal item
                        "MHHDVu": item.get("id") or "",
                        "THHDVu": item.get("item_name") or "",
                        "DVTinh": item.get("unit") or "",
                        "SLuong": item.get("quantity") or 0.0,
                        "DGia": item.get("unit_price") or 0.0,
                        "ThTien": item.get("amount_before_tax") or 0.0,
                        "TSuat": item.get("tax_rate") or "10%",
                        "TLCKhau": 0.0,
                        "STCKhau": 0.0
                    })
                    stt_counter += 1
            except Exception as item_err:
                logger.warning(f"Could not load line items for invoice {inv['id']}: {item_err}")
                
        return jsonify(all_items)
    except Exception as e:
        logger.error(f"Error fetching purchase items for smart-invoice API: {e}")
        return jsonify({"error": f"Loi truy van chi tiet mat hang: {str(e)}"}), 500
    finally:
        # Restore configuration JWT
        current_app.config["CURRENT_JWT"] = original_jwt
