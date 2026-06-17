"""Invoice retrieval services with mock data and live GDT integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import requests
from flask import current_app

from invoices.parser import normalize_invoice


@dataclass(frozen=True)
class InvoiceQuery:
    """Typed query container used by routes and tests."""

    date_from: date
    date_to: date
    cancelled_only: bool = False
    direction: str = "purchase"


MOCK_INVOICES = [
    {
        "id": "INV-2026-0501",
        "date": "2026-05-01",
        "amount": 1540000,
        "status": "valid",
        "issuer": "Cong ty A",
        "description": "Hoa don dau vao thang 5",
        "is_cancelled": False,
        "line_items": [
            {
                "item_name": "Laptop Dell Vostro 3520",
                "quantity": 1,
                "unit_price": 1200000,
                "amount_before_tax": 1200000,
                "tax_rate": "10%",
                "tax_amount": 120000,
            },
            {
                "item_name": "Chuot khong day Logitech M331",
                "quantity": 2,
                "unit_price": 100000,
                "amount_before_tax": 200000,
                "tax_rate": "10%",
                "tax_amount": 20000,
            },
        ],
    },
    {
        "id": "INV-2026-0508",
        "date": "2026-05-08",
        "amount": 2700000,
        "status": "cancelled",
        "issuer": "Cong ty B",
        "description": "Hoa don bi huy",
        "is_cancelled": True,
        "cancellation_date": "2026-05-12",
        "cancellation_reason": "Sai thong tin nguoi mua",
        "line_items": [
            {
                "item_name": "Ban lam viec go soi",
                "quantity": 1,
                "unit_price": 2000000,
                "amount_before_tax": 2000000,
                "tax_rate": "8%",
                "tax_amount": 160000,
            },
            {
                "item_name": "Ghe xoay van phong",
                "quantity": 1,
                "unit_price": 500000,
                "amount_before_tax": 500000,
                "tax_rate": "8%",
                "tax_amount": 40000,
            },
        ],
    },
    {
        "id": "INV-2026-0518",
        "date": "2026-05-18",
        "amount": 972000,
        "status": "valid",
        "issuer": "Cong ty C",
        "description": "Dich vu logistics",
        "is_cancelled": False,
        "line_items": [
            {
                "item_name": "Phi dich vu logistics thang 5",
                "quantity": 1,
                "unit_price": 900000,
                "amount_before_tax": 900000,
                "tax_rate": "8%",
                "tax_amount": 72000,
            }
        ],
    },
]


class GDTIntegrationNotReadyError(RuntimeError):
    """Raised when live integration cannot proceed with current inputs."""


def fetch_invoices(query: InvoiceQuery) -> list[dict]:
    """Return invoices for the requested range using mock data or live integration."""

    if current_app.config["GDT_USE_MOCK"]:
        results = []
        for raw_invoice in MOCK_INVOICES:
            invoice_date = date.fromisoformat(raw_invoice["date"])
            if not (query.date_from <= invoice_date <= query.date_to):
                continue
            if query.cancelled_only and not raw_invoice.get("is_cancelled", False):
                continue
            results.append(normalize_invoice(raw_invoice))
        return results

    jwt_token = None
    try:
        from invoices.thread_local import get_current_thread_credentials
        _, _, tl_jwt = get_current_thread_credentials()
        jwt_token = tl_jwt
    except ImportError:
        pass

    if not jwt_token:
        jwt_token = current_app.config.get("CURRENT_JWT")

    if not jwt_token:
        from auth.service import auto_refresh_gdt_session
        if auto_refresh_gdt_session():
            try:
                from invoices.thread_local import get_current_thread_credentials
                _, _, tl_jwt = get_current_thread_credentials()
                jwt_token = tl_jwt
            except ImportError:
                pass
            if not jwt_token:
                jwt_token = current_app.config.get("CURRENT_JWT")
        else:
            raise GDTIntegrationNotReadyError("Chua co JWT dang nhap de goi danh sach hoa don.")

    endpoint = "purchase" if query.direction != "sold" else "sold"
    
    attempts = 2
    for attempt in range(attempts):
        jwt_token = None
        try:
            from invoices.thread_local import get_current_thread_credentials
            _, _, tl_jwt = get_current_thread_credentials()
            jwt_token = tl_jwt
        except ImportError:
            pass
        if not jwt_token:
            jwt_token = current_app.config.get("CURRENT_JWT")
        from auth.gdt_client import gdt_request
        response = gdt_request(
            "GET",
            f"api/query/invoices/{endpoint}",
            params={
                "sort": "tdlap:desc",
                "size": 100,
                "search": _build_search_string(query),
            },
            headers={
                "Authorization": f"Bearer {jwt_token}",
            },
        )
        if response.status_code == 401 and attempt == 0:
            current_app.logger.warning("GDT session expired (401) in fetch_invoices. Attempting auto-refresh...")
            from auth.service import auto_refresh_gdt_session
            if auto_refresh_gdt_session():
                continue  # Retry with new token

        if response.status_code >= 400:
            raise GDTIntegrationNotReadyError(_extract_live_error(response))

        payload = response.json()
        rows = payload.get("datas") or payload.get("data") or payload.get("items") or []
        invoices = [_normalize_live_invoice(row) for row in rows]
        if query.cancelled_only:
            invoices = [invoice for invoice in invoices if invoice.get("is_cancelled")]
        return invoices



def get_invoice_by_id(invoice_id: str) -> dict | None:
    """Return one invoice by id from the current data source."""

    for raw_invoice in MOCK_INVOICES:
        if raw_invoice["id"] == invoice_id:
            return normalize_invoice(raw_invoice)
    return None


def download_invoice_xml(invoice_id: str) -> bytes:
    """Download invoice XML. Returns bytes."""
    
    # Fast path: check if local XML file exists in data/invoices_xml
    local_xml_path = os.path.join(XML_DIR, f"invoice_{invoice_id}.xml")
    if os.path.exists(local_xml_path):
        with open(local_xml_path, "rb") as f:
            return f.read()

    # If mock mode is enabled, generate mock XML
    if current_app.config.get("GDT_USE_MOCK", False):
        invoice = get_invoice_by_id(invoice_id)
        if not invoice:
            raise FileNotFoundError("Khong tim thay hoa don can tai.")

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<invoice>
  <id>{invoice["id"]}</id>
  <date>{invoice["date"]}</date>
  <amount>{invoice["amount"]}</amount>
  <status>{invoice["status"]}</status>
  <issuer>{invoice["issuer"]}</issuer>
  <description>{invoice["description"]}</description>
</invoice>
"""
        return xml.encode("utf-8")

    # Otherwise, download from GDT (Live mode)
    jwt_token = None
    try:
        from invoices.thread_local import get_current_thread_credentials
        _, _, tl_jwt = get_current_thread_credentials()
        jwt_token = tl_jwt
    except ImportError:
        pass
    if not jwt_token:
        jwt_token = current_app.config.get("CURRENT_JWT")

    if not jwt_token:
        from auth.service import auto_refresh_gdt_session
        if auto_refresh_gdt_session():
            try:
                from invoices.thread_local import get_current_thread_credentials
                _, _, tl_jwt = get_current_thread_credentials()
                jwt_token = tl_jwt
            except ImportError:
                pass
            if not jwt_token:
                jwt_token = current_app.config.get("CURRENT_JWT")
        else:
            raise GDTIntegrationNotReadyError("Chua co JWT dang nhap de tai XML.")

    invoice = None
    try:
        from invoices.thread_local import get_current_thread_lookup
        tl_lookup = get_current_thread_lookup()
        if tl_lookup:
            invoice = tl_lookup.get(invoice_id)
    except ImportError:
        pass
    if not invoice:
        invoice = current_app.config.get("CURRENT_INVOICE_LOOKUP", {}).get(invoice_id)
    if not invoice:
        raise FileNotFoundError("Khong tim thay hoa don trong phien hien tai de tai XML.")
    raw_invoice = invoice.get("raw") or {}
    if not raw_invoice.get("hsgoc"):
        raise NotImplementedError("Hoa don nay khong co ho so goc de xuat XML.")
    endpoint = "sco-query" if _is_cash_register_invoice(raw_invoice) else "query"
    export_params = {
        "nbmst": raw_invoice.get("nbmst"),
        "khhdon": raw_invoice.get("khhdon"),
        "shdon": raw_invoice.get("shdon"),
        "khmshdon": raw_invoice.get("khmshdon"),
    }
    
    attempts = 2
    for attempt in range(attempts):
        jwt_token = None
        try:
            from invoices.thread_local import get_current_thread_credentials
            _, _, tl_jwt = get_current_thread_credentials()
            jwt_token = tl_jwt
        except ImportError:
            pass
        if not jwt_token:
            jwt_token = current_app.config.get("CURRENT_JWT")
        from auth.gdt_client import gdt_request
        response = gdt_request(
            "GET",
            f"api/{endpoint}/invoices/export-xml",
            params=export_params,
            headers={
                "Authorization": f"Bearer {jwt_token}",
            },
        )
        if response.status_code == 401 and attempt == 0:
            current_app.logger.warning("GDT session expired (401) in download_invoice_xml. Attempting auto-refresh...")
            from auth.service import auto_refresh_gdt_session
            if auto_refresh_gdt_session():
                continue  # Retry with new token

        if response.status_code >= 400:
            raise GDTIntegrationNotReadyError(_extract_live_error(response))
        return response.content


def _build_search_string(query: InvoiceQuery) -> str:
    """Build the `search=` format discovered from the production Next.js bundle."""

    start = f"{query.date_from.isoformat()}T00:00:00.000Z"
    end = f"{query.date_to.isoformat()}T23:59:59.999Z"
    return f"tdlap=ge={start};tdlap=le={end}"


def _normalize_live_invoice(raw_invoice: dict) -> dict:
    """Convert GDT invoice rows into the UI structure expected by the app."""

    invoice_id = (
        raw_invoice.get("id")
        or raw_invoice.get("shdon")
        or raw_invoice.get("so")
        or raw_invoice.get("invoiceId")
        or "unknown"
    )
    raw_date = raw_invoice.get("tdlap") or raw_invoice.get("ngay") or raw_invoice.get("date")
    status = str(raw_invoice.get("tthai") or raw_invoice.get("status") or raw_invoice.get("trthai") or "")
    issuer = (
        raw_invoice.get("nbten")
        or raw_invoice.get("tnban")
        or raw_invoice.get("sellerName")
        or raw_invoice.get("tnmua")
        or ""
    )
    amount = (
        raw_invoice.get("tgtcthue")
        or raw_invoice.get("tgtttbso")
        or raw_invoice.get("tgtttbchu")
        or raw_invoice.get("amount")
        or 0
    )
    return {
        "id": str(invoice_id),
        "date": _normalize_live_date(raw_date),
        "amount": _coerce_amount(amount),
        "status": status or "unknown",
        "issuer": issuer or "Khong ro",
        "description": raw_invoice.get("khhdon") or raw_invoice.get("mst") or "",
        "is_cancelled": "huy" in status.lower() or "cancel" in status.lower(),
        "cancellation_date": None,
        "cancellation_reason": raw_invoice.get("lydo") or raw_invoice.get("reason"),
        "raw": raw_invoice,
    }


def build_invoice_lookup(invoices: list[dict]) -> dict[str, dict]:
    """Build an in-memory lookup table for later XML export requests."""

    return {invoice["id"]: invoice for invoice in invoices if invoice.get("id")}


def resolve_live_download_name(invoice: dict) -> str:
    """Return a filename for XML/ZIP downloads based on live invoice fields."""

    raw_invoice = invoice.get("raw") or {}
    suffix = "zip" if raw_invoice.get("hsgoc") else "xml"
    return f'invoice_{invoice["id"]}.{suffix}'


def _normalize_live_date(value) -> str:
    """Convert several date representations into YYYY-MM-DD."""

    if not value:
        return ""
    if isinstance(value, str):
        cleaned = value.strip()
        if "T" in cleaned:
            return cleaned.split("T", 1)[0]
        if len(cleaned) >= 10 and cleaned[4] == "-" and cleaned[7] == "-":
            return cleaned[:10]
        if len(cleaned) >= 10 and cleaned[2] == "/" and cleaned[5] == "/":
            day, month, year = cleaned[:10].split("/")
            return f"{year}-{month}-{day}"
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000).date().isoformat()
    return str(value)


def _coerce_amount(value) -> float:
    """Best-effort numeric coercion for money fields."""

    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        digits = value.replace(".", "").replace(",", "").strip()
        return float(digits) if digits.isdigit() else 0
    return 0


def _extract_live_error(response: requests.Response) -> str:
    """Read upstream GDT error payloads into a user-facing message."""

    try:
        payload = response.json()
    except ValueError:
        return "Khong the doc phan hoi loi tu he thong thue."
    return payload.get("message") or payload.get("error") or "Goi API he thong thue that bai."


def _is_cash_register_invoice(raw_invoice: dict) -> bool:
    """Detect tax-machine invoices the same way production bundle does."""

    khhdon = str(raw_invoice.get("khhdon") or "")
    return len(khhdon) >= 4 and khhdon[3] == "M"


def fetch_invoice_line_items(invoice_id: str) -> list[dict]:
    """Fetch line items for a given invoice (mock or live GDT XML parsing)."""

    # Check local database first
    local_invoices = get_local_invoices()
    for item in local_invoices:
        if item["id"] == invoice_id:
            # Map local invoice item fields to line items expected format
            mapped_items = []
            for row in item.get("items", []):
                mapped_items.append({
                    "id": row.get("id"),
                    "item_name": row.get("item_name", ""),
                    "quantity": row.get("quantity", 0.0),
                    "unit_price": row.get("unit_price", 0.0),
                    "amount_before_tax": row.get("amount_before_tax", 0.0),
                    "tax_rate": row.get("tax_rate", "10%"),
                    "tax_amount": row.get("tax_amount", 0.0),
                    "expense_category": row.get("expense_category", "Chưa phân loại"),
                })
            return mapped_items

    if current_app.config["GDT_USE_MOCK"]:
        invoice = get_invoice_by_id(invoice_id)
        if not invoice:
            raise FileNotFoundError("Khong tim thay hoa don trong he thong mock.")
        return invoice.get("line_items") or []

    # Live Mode
    # Download XML bytes
    xml_bytes = download_invoice_xml(invoice_id)
    # Parse line items from XML
    from invoices.parser import parse_xml_line_items

    return parse_xml_line_items(xml_bytes)


def extract_partners_from_invoices(invoices: list[dict]) -> list[dict]:
    """Extract unique business partners from a list of invoices and compute transaction metrics."""
    from extensions import db
    from invoices.models import Partner

    partner_map = {}

    # Predefined info map for known issuers
    partner_details = {
        "Cong ty A": {"mst": "0101234567", "address": "So 10 Pho Hue, Quan Hai Ba Trung, Ha Noi"},
        "Cong ty B": {"mst": "0209876543", "address": "250 Nguyen Thi Minh Khai, Quan 3, TP. Ho Chi Minh"},
        "Cong ty C": {"mst": "0301122334", "address": "15 Le Loi, Quan Hai Chau, Da Nang"},
    }

    for inv in invoices:
        issuer = inv.get("issuer", "Doi tac khac")
        amount = inv.get("amount", 0.0)
        is_cancelled = inv.get("is_cancelled", False)

        if issuer not in partner_map:
            # Query db first
            partner_record = Partner.query.filter_by(name=issuer).first()
            if partner_record:
                mst = partner_record.mst
                address = partner_record.address
                status = partner_record.mst_status or "Chưa xác định (Lỗi kết nối)"
            else:
                # Fallback details
                details = partner_details.get(
                    issuer,
                    {
                        "mst": f"0{abs(hash(issuer)) % 1000000000:09d}",
                        "address": f"Khu cong nghiep, Quan Binh Thanh, TP. Ho Chi Minh",
                    }
                )
                mst = details["mst"]
                address = details["address"]
                
                # Check live/mock status
                from invoices.mst_service import check_mst_status
                status_info = check_mst_status(mst)
                status = status_info.get("status", "Chưa xác định (Lỗi kết nối)")
                
                # Persist partner
                try:
                    partner_record = Partner(
                        mst=mst,
                        name=issuer,
                        address=address,
                        mst_status=status,
                        mst_last_checked=datetime.now().isoformat()
                    )
                    db.session.add(partner_record)
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            partner_map[issuer] = {
                "name": issuer,
                "mst": mst,
                "address": address,
                "mst_status": status,
                "total_spend": 0.0,
                "transaction_count": 0,
                "cancelled_count": 0,
            }

        partner_map[issuer]["transaction_count"] += 1
        if is_cancelled:
            partner_map[issuer]["cancelled_count"] += 1
        else:
            partner_map[issuer]["total_spend"] += amount

    return sorted(list(partner_map.values()), key=lambda x: x["total_spend"], reverse=True)



def generate_tax_usage_report(invoices: list[dict]) -> list[dict]:
    """Compile the Vietnamese official BC26 tax invoice usage statistics by invoice template symbol."""

    report_map = {}

    for inv in invoices:
        inv_id = str(inv.get("id") or "")
        symbol = "1C26TBA" if "-" not in inv_id else f"1C26{inv_id.split('-')[1]}"

        try:
            num_part = inv_id.split("-")[-1]
            number_val = int("".join(filter(str.isdigit, num_part)))
        except (ValueError, IndexError):
            number_val = 1

        is_cancelled = inv.get("is_cancelled", False)

        if symbol not in report_map:
            report_map[symbol] = {
                "symbol": symbol,
                "numbers": [],
                "cancelled_numbers": [],
                "active_numbers": [],
            }

        report_map[symbol]["numbers"].append(number_val)
        if is_cancelled:
            report_map[symbol]["cancelled_numbers"].append(number_val)
        else:
            report_map[symbol]["active_numbers"].append(number_val)

    report_list = []
    for symbol, data in report_map.items():
        all_nums = sorted(data["numbers"])
        start_num = all_nums[0] if all_nums else 0
        end_num = all_nums[-1] if all_nums else 0

        total_used = len(all_nums)
        cancelled_count = len(data["cancelled_numbers"])
        active_count = len(data["active_numbers"])

        cancelled_str = ", ".join(f"{n:07d}" for n in sorted(data["cancelled_numbers"])) if data["cancelled_numbers"] else "-"

        report_list.append({
            "symbol": symbol,
            "start_number": f"{start_num:07d}",
            "end_number": f"{end_num:07d}",
            "total_used": total_used,
            "active_count": active_count,
            "cancelled_count": cancelled_count,
            "cancelled_numbers": cancelled_str,
        })

    return report_list


import os
import json
import zipfile
from io import BytesIO

DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "invoices_db.json")
XML_DIR = os.path.join(DB_DIR, "invoices_xml")

# Initialize directories
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(XML_DIR, exist_ok=True)


def migrate_legacy_json_to_sqlite() -> None:
    """One-time migration of flat file invoices_db.json to SQLite database."""
    import shutil
    from extensions import db
    from invoices.models import Invoice, LineItem, Partner, SystemConfig, SchedulerLog

    if not os.path.exists(DB_FILE):
        return

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            if isinstance(data, list):
                data = {"invoices": data, "partners": []}
            else:
                data = {"invoices": [], "partners": []}

        # Backup file to .bak
        shutil.copy2(DB_FILE, DB_FILE + ".bak")

        # Migrate Invoices
        for inv_data in data.get("invoices", []):
            if not inv_data.get("id"):
                continue
            if db.session.get(Invoice, inv_data["id"]):
                continue

            inv = Invoice(
                id=inv_data["id"],
                filename=inv_data.get("filename"),
                invoice_type=inv_data.get("invoice_type"),
                template_code=inv_data.get("template_code"),
                symbol=inv_data.get("symbol"),
                number=inv_data.get("number"),
                date=inv_data.get("date"),
                currency=inv_data.get("currency"),
                seller_name=inv_data.get("seller_name"),
                seller_mst=inv_data.get("seller_mst"),
                seller_address=inv_data.get("seller_address"),
                seller_phone=inv_data.get("seller_phone"),
                buyer_name=inv_data.get("buyer_name"),
                buyer_mst=inv_data.get("buyer_mst"),
                buyer_address=inv_data.get("buyer_address"),
                amount_before_tax=inv_data.get("amount_before_tax", 0.0),
                tax_amount=inv_data.get("tax_amount", 0.0),
                total_amount=inv_data.get("total_amount", 0.0),
                has_signature=inv_data.get("has_signature", False),
                signing_date=inv_data.get("signing_date"),
                payment_method=inv_data.get("payment_method"),
                is_cancelled=inv_data.get("is_cancelled", False),
                cancellation_date=inv_data.get("cancellation_date"),
                cancellation_reason=inv_data.get("cancellation_reason"),
                notes=inv_data.get("notes"),
                imported_at=inv_data.get("imported_at") or datetime.now().isoformat(),
                updated_at=inv_data.get("updated_at"),
                import_status=inv_data.get("import_status", "imported"),
                invoice_status=inv_data.get("invoice_status") or ("Bị hủy" if inv_data.get("is_cancelled") else "Gốc")
            )

            inv.warnings = inv_data.get("warnings", [])
            db.session.add(inv)

            for item_data in inv_data.get("items", []):
                item = LineItem(
                    invoice_id=inv.id,
                    item_name=item_data["item_name"],
                    unit=item_data.get("unit"),
                    quantity=item_data.get("quantity", 0.0),
                    unit_price=item_data.get("unit_price", 0.0),
                    amount_before_tax=item_data.get("amount_before_tax", 0.0),
                    tax_rate=item_data.get("tax_rate", "0%"),
                    tax_amount=item_data.get("tax_amount", 0.0)
                )
                db.session.add(item)

        # Migrate Partners
        for p_data in data.get("partners", []):
            if not p_data.get("mst"):
                continue
            if db.session.get(Partner, p_data["mst"]):
                continue

            partner = Partner(
                mst=p_data["mst"],
                name=p_data.get("name"),
                address=p_data.get("address"),
                mst_status=p_data.get("mst_status"),
                mst_last_checked=p_data.get("mst_last_checked")
            )
            db.session.add(partner)

        # Migrate Settings
        settings = data.get("settings", {})
        for key, val in settings.items():
            if db.session.get(SystemConfig, key):
                continue
            cfg = SystemConfig(key=key, value=str(val))
            db.session.add(cfg)

        # Migrate Logs
        for log_data in data.get("scheduler_logs", []):
            log = SchedulerLog(
                timestamp=log_data.get("timestamp") or datetime.now().isoformat(),
                status=log_data.get("status") or "SUCCESS",
                details=log_data.get("details")
            )
            db.session.add(log)

        db.session.commit()

        # Delete legacy JSON file after successful migration
        try:
            os.remove(DB_FILE)
        except Exception:
            pass
    except Exception:
        db.session.rollback()


def get_local_invoices(taxpayer_mst: str | None = None) -> list[dict]:
    """Read all parsed invoices from the local database, merged with zipped cold storage (US-125)."""
    try:
        from extensions import db
        from invoices.models import Invoice
        from invoices.archiver import InvoiceArchiver
        
        if taxpayer_mst:
            invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst).all()
        else:
            invoices = Invoice.query.all()
            
        live_list = [inv.to_dict() for inv in invoices]
        cold_list = InvoiceArchiver.get_archived_invoices(taxpayer_mst)
        
        seen_ids = {inv["id"] for inv in live_list}
        merged = list(live_list)
        for inv in cold_list:
            if inv["id"] not in seen_ids:
                merged.append(inv)
                
        merged.sort(key=lambda x: x.get("date", ""), reverse=True)
        return merged
    except Exception as e:
        return []


def _save_local_invoices(invoices: list[dict]) -> None:
    """Save the list of invoices to the local database (upsert)."""
    from extensions import db
    from invoices.models import Invoice, LineItem
    try:
        for inv_data in invoices:
            invoice = db.session.get(Invoice, inv_data["id"])
            if not invoice:
                invoice = Invoice(id=inv_data["id"])
                db.session.add(invoice)
            
            invoice.filename = inv_data.get("filename")
            invoice.invoice_type = inv_data.get("invoice_type")
            invoice.template_code = inv_data.get("template_code")
            invoice.symbol = inv_data.get("symbol")
            invoice.number = inv_data.get("number")
            invoice.date = inv_data.get("date")
            invoice.currency = inv_data.get("currency")
            invoice.seller_name = inv_data.get("seller_name")
            invoice.seller_mst = inv_data.get("seller_mst")
            invoice.seller_address = inv_data.get("seller_address")
            invoice.seller_phone = inv_data.get("seller_phone")
            invoice.buyer_name = inv_data.get("buyer_name")
            invoice.buyer_mst = inv_data.get("buyer_mst")
            invoice.buyer_address = inv_data.get("buyer_address")
            invoice.amount_before_tax = inv_data.get("amount_before_tax", 0.0)
            invoice.tax_amount = inv_data.get("tax_amount", 0.0)
            invoice.total_amount = inv_data.get("total_amount", 0.0)
            invoice.has_signature = inv_data.get("has_signature", False)
            invoice.signing_date = inv_data.get("signing_date")
            invoice.payment_method = inv_data.get("payment_method")
            invoice.is_cancelled = inv_data.get("is_cancelled", False)
            invoice.cancellation_date = inv_data.get("cancellation_date")
            invoice.cancellation_reason = inv_data.get("cancellation_reason")
            invoice.warnings = inv_data.get("warnings", [])
            invoice.notes = inv_data.get("notes")
            invoice.imported_at = inv_data.get("imported_at") or datetime.now().isoformat()
            invoice.updated_at = inv_data.get("updated_at")
            invoice.import_status = inv_data.get("import_status", "imported")
            
            # Recreate items
            LineItem.query.filter_by(invoice_id=invoice.id).delete()
            for item_data in inv_data.get("items", []):
                item = LineItem(
                    invoice_id=invoice.id,
                    item_name=item_data["item_name"],
                    unit=item_data.get("unit"),
                    quantity=item_data.get("quantity", 0.0),
                    unit_price=item_data.get("unit_price", 0.0),
                    amount_before_tax=item_data.get("amount_before_tax", 0.0),
                    tax_rate=item_data.get("tax_rate", "0%"),
                    tax_amount=item_data.get("tax_amount", 0.0)
                )
                db.session.add(item)
        db.session.commit()
        # Invalidate stats cache on successful invoice storage (US-124)
        from invoices.stats_cache import invalidate_stats_cache
        invalidate_stats_cache(None)  # Invalidate global cache
        for inv_data in invoices:
            invalidate_stats_cache(inv_data.get("buyer_mst"))
            invalidate_stats_cache(inv_data.get("seller_mst"))
            invalidate_stats_cache(inv_data.get("taxpayer_mst"))
    except Exception:
        db.session.rollback()



def _run_smart_audits(invoice: dict, local_db: list[dict]) -> list[str]:
    """Run four MISA-style smart audits on the invoice and return warning messages."""

    warnings = []

    # 1. Duplicate Check
    seller_mst = invoice.get("seller_mst", "")
    symbol = invoice.get("symbol", "")
    number = invoice.get("number", "")

    is_duplicate = False
    for item in local_db:
        # Match identical seller MST + symbol + number to identify duplicates
        if item.get("seller_mst") == seller_mst and item.get("symbol") == symbol and item.get("number") == number:
            is_duplicate = True
            break
    if is_duplicate:
        warnings.append("Hóa đơn đã tồn tại trong hệ thống (Trùng MST người bán, ký hiệu và số hóa đơn).")

    # 2. Tax Mismatch Check
    total_calculated_tax = 0.0
    for item in invoice.get("items", []):
        rate_str = item.get("tax_rate", "10%")
        try:
            if "10" in rate_str:
                rate_val = 0.10
            elif "8" in rate_str:
                rate_val = 0.08
            elif "5" in rate_str:
                rate_val = 0.05
            elif "0" in rate_str:
                rate_val = 0.0
            else:
                rate_val = 0.0
        except Exception:
            rate_val = 0.10
        total_calculated_tax += item.get("amount_before_tax", 0.0) * rate_val

    declared_tax = invoice.get("tax_amount", 0.0)
    if abs(total_calculated_tax - declared_tax) > 10.0:
        warnings.append(f"Chênh lệch thuế suất: Tính toán lại là {total_calculated_tax:,.0f} VND nhưng khai báo là {declared_tax:,.0f} VND.")

    # 3. High-Risk / Blacklisted MST Check
    from invoices.models import BlacklistedMST
    from extensions import db
    is_blacklisted = False
    if seller_mst:
        try:
            blacklisted_record = db.session.get(BlacklistedMST, seller_mst)
            if blacklisted_record:
                is_blacklisted = True
        except Exception:
            pass

    if is_blacklisted:
        warnings.append(f"CRITICAL_BLACKLIST_ALERT: MST Người bán ({seller_mst}) nằm trong danh sách đen của GDT (phát hiện rủi ro trốn thuế/hóa đơn khống).")
    else:
        HIGH_RISK_MSTS = {"0101234599", "0209876599", "0301122399"}
        if seller_mst in HIGH_RISK_MSTS:
            warnings.append(f"MST Người bán ({seller_mst}) thuộc danh mục doanh nghiệp rủi ro cao về thuế của Cơ quan Thuế.")

    # 4. Digital Signature Check
    if not invoice.get("has_signature", False):
        warnings.append("Hóa đơn chưa được ký số hoặc tệp tin XML bị sửa đổi làm hỏng chữ ký số.")

    # 5. Delayed Digital Signature Check
    signing_date = invoice.get("signing_date")
    invoice_date_str = invoice.get("date", "")
    if signing_date and invoice_date_str:
        try:
            inv_date = datetime.strptime(invoice_date_str[:10], "%Y-%m-%d").date()
            sig_date = datetime.strptime(signing_date[:10], "%Y-%m-%d").date()
            if (sig_date - inv_date).days > 1:
                inv_formatted = inv_date.strftime("%d/%m/%Y")
                sig_formatted = sig_date.strftime("%d/%m/%Y")
                warnings.append(f"Hóa đơn ký số chậm (Ngày lập: {inv_formatted}, Ngày ký: {sig_formatted}) - Rủi ro thuế và thời điểm kê khai.")
        except Exception:
            pass

    # 6. Payment Method Compliance Check (VAT Law 2024 - 5M VND non-cash threshold)
    payment_method = invoice.get("payment_method", "")
    total_amount = invoice.get("total_amount", 0.0)
    if total_amount >= 5000000.0 and payment_method:
        pm_lower = payment_method.lower()
        is_cash = any(x in pm_lower for x in ["tm", "tiền mặt", "cash"])
        is_non_cash = any(x in pm_lower for x in ["ck", "chuyển khoản", "ngân hàng", "đối trừ", "bù trừ", "nh", "banking"])
        if is_cash and not is_non_cash:
            warnings.append(
                f"Hóa đơn có giá trị từ 5 triệu VND trở lên ({total_amount:,.0f} VND) nhưng ghi nhận phương thức thanh toán là '{payment_method}'. "
                "Theo Luật Thuế GTGT 2024 (hiệu lực từ 01/07/2025), giao dịch từ 5 triệu VND trở lên bắt buộc phải thanh toán không dùng tiền mặt (chuyển khoản) để được khấu trừ thuế GTGT đầu vào."
            )

    # 7. Seller MST status check
    if seller_mst:
        from invoices.mst_service import check_mst_status, STATUS_ACTIVE
        mst_info = check_mst_status(seller_mst)
        status = mst_info.get("status", "")
        if status != STATUS_ACTIVE:
            warnings.append(f"Mã số thuế người bán ({seller_mst}) ở trạng thái '{status}'. Nguy cơ hóa đơn bất hợp lệ.")

    return warnings


def recalculate_t_score_value(invoice) -> tuple[int, str]:
    """
    Calculate compliance T-Score (0-100) and letter rating (A++, A, B, C, D, F)
    based on compliance warnings, signature timing, MST status, payment compliance, and AI audits.
    """
    score = 100
    
    # 1. Partner MST status check: if not STATUS_ACTIVE or is high-risk MST, deduct 40.
    # If blacklisted MST, T-Score drops immediately to 0 and rating to F.
    from extensions import db
    from invoices.models import Partner, BlacklistedMST
    from invoices.mst_service import check_mst_status, STATUS_ACTIVE
    
    seller_mst = invoice.seller_mst
    if seller_mst:
        is_blacklisted = False
        try:
            blacklisted_record = db.session.get(BlacklistedMST, seller_mst)
            if blacklisted_record:
                is_blacklisted = True
        except Exception:
            pass

        if is_blacklisted:
            return 0, "F"

        # Check high risk MST
        HIGH_RISK_MSTS = {"0101234599", "0209876599", "0301122399"}
        if seller_mst in HIGH_RISK_MSTS:
            score -= 40
        else:
            partner = db.session.get(Partner, seller_mst)
            mst_status = partner.mst_status if partner else None
            if not mst_status:
                mst_info = check_mst_status(seller_mst)
                mst_status = mst_info.get("status", "")
            
            if mst_status and mst_status != STATUS_ACTIVE:
                score -= 40
    
    # 2. Digital signature verification and tampering check: if not signed, deduct 20; if tampered/invalid, drop to 0.
    if not invoice.has_signature:
        score -= 20
    else:
        sig_details = getattr(invoice, "signature_details", None)
        if sig_details:
            if not sig_details.get("sig_verified", False) or sig_details.get("sig_tampered_nodes"):
                return 0, "F"
        
    # 3. Late signature (> 1 day): deduct 20
    signing_date = invoice.signing_date
    invoice_date_str = invoice.date
    if signing_date and invoice_date_str:
        try:
            inv_date = datetime.strptime(invoice_date_str[:10], "%Y-%m-%d").date()
            sig_date = datetime.strptime(signing_date[:10], "%Y-%m-%d").date()
            if (sig_date - inv_date).days > 1:
                score -= 20
        except Exception:
            pass

    # 4. Tax mismatch: deduct 20
    # Calculate tax rate vs declared tax
    total_calculated_tax = 0.0
    for item in invoice.items:
        rate_str = item.tax_rate or "10%"
        try:
            if "10" in rate_str:
                rate_val = 0.10
            elif "8" in rate_str:
                rate_val = 0.08
            elif "5" in rate_str:
                rate_val = 0.05
            elif "0" in rate_str:
                rate_val = 0.0
            else:
                rate_val = 0.0
        except Exception:
            rate_val = 0.10
        total_calculated_tax += (item.amount_before_tax or 0.0) * rate_val

    declared_tax = invoice.tax_amount or 0.0
    if abs(total_calculated_tax - declared_tax) > 10.0:
        score -= 20

    # 5. Cash payment compliance check (VAT Law 2024 - 5M VND non-cash threshold)
    payment_method = invoice.payment_method
    total_amount = invoice.total_amount or 0.0
    if total_amount >= 5000000.0 and payment_method:
        pm_lower = payment_method.lower()
        is_cash = any(x in pm_lower for x in ["tm", "tiền mặt", "cash"])
        is_non_cash = any(x in pm_lower for x in ["ck", "chuyển khoản", "ngân hàng", "đối trừ", "bù trừ", "nh", "banking"])
        if is_cash and not is_non_cash:
            score -= 20

    # 6. AI Compliance warnings: deduct 15 per warning, cap at 30
    ai_warning_count = len(invoice.ai_audit_results) if invoice.ai_audit_results else 0
    ai_deduction = ai_warning_count * 15
    if ai_deduction > 30:
        ai_deduction = 30
    score -= ai_deduction

    # Clamp score to [0, 100]
    score = max(0, min(100, score))

    # Calculate rating
    if score >= 95:
        rating = "A++"
    elif score >= 90:
        rating = "A"
    elif score >= 80:
        rating = "B"
    elif score >= 70:
        rating = "C"
    elif score >= 50:
        rating = "D"
    else:
        rating = "F"

    return score, rating


def calculate_invoice_t_score(invoice) -> tuple[int, str]:
    """Calculate and save T-Score and rating to database for the given invoice."""
    score, rating = recalculate_t_score_value(invoice)
    invoice.t_score = score
    invoice.t_rating = rating
    return score, rating


def import_xml_invoice(xml_bytes: bytes, filename: str, duplicate_strategy: str = "overwrite", taxpayer_mst: str | None = None) -> dict:
    """Parse, run smart audits, and save XML invoice to local database."""
    from extensions import db
    from invoices.models import Invoice, LineItem
    from invoices.parser import parse_complete_xml
    from invoices.schema_validator import validate_xml_schema

    # Run XSD validation
    schema_valid, schema_err = validate_xml_schema(xml_bytes)

    # Parse invoice XML
    parsed_invoice = parse_complete_xml(xml_bytes)

    invoice_id = f"{parsed_invoice['seller_mst']}-{parsed_invoice['symbol']}-{parsed_invoice['number']}"
    
    # Load system settings for security gatekeepers
    from invoices.scheduler import load_scheduler_settings
    settings = load_scheduler_settings()
    
    signature_filter_enabled = settings.get("signature_filter_enabled", True)
    blacklist_filter_enabled = settings.get("blacklist_filter_enabled", True)

    seller_mst = parsed_invoice.get("seller_mst", "")
    
    # 1. Blacklist check block
    if blacklist_filter_enabled and seller_mst:
        from invoices.models import BlacklistedMST
        blacklisted_record = db.session.get(BlacklistedMST, seller_mst)
        if blacklisted_record:
            reason = blacklisted_record.reason or "Không rõ lý do"
            raise ValueError(f"Hóa đơn bị TỪ CHỐI import do MST người bán ({seller_mst}) nằm trong DANH SÁCH ĐEN chống gian lận thuế (Lý do: {reason}).")

    # 2. Signature verification
    from invoices.signature_verifier import verify_xml_signature
    sig_details = verify_xml_signature(
        xml_bytes,
        invoice_date_str=parsed_invoice.get("date"),
        seller_mst=parsed_invoice.get("seller_mst"),
        seller_name=parsed_invoice.get("seller_name")
    )
    
    if signature_filter_enabled:
        if not parsed_invoice.get("has_signature"):
            raise ValueError("Hóa đơn bị TỪ CHỐI import do cấu hình Bộ lọc bảo mật: Hóa đơn hoàn toàn không chứa chữ ký số (Digital Signature).")
        
        if not sig_details.get("sig_verified"):
            sig_err = sig_details.get("sig_error") or "Chữ ký số không hợp lệ hoặc bị lỗi xác thực."
            raise ValueError(f"Hóa đơn bị TỪ CHỐI import do cấu hình Bộ lọc bảo mật: Chữ ký số không hợp lệ ({sig_err}).")
            
        if sig_details.get("sig_tampered_nodes"):
            raise ValueError("CẢNH BÁO BẢO MẬT: Hóa đơn bị TỪ CHỐI import do phát hiện nội dung XML đã bị THAY ĐỔI hoặc GIẢ MẠO sau khi ký số (Cryptographic Tampering detected).")

    # Get existing record if any
    existing_record = db.session.get(Invoice, invoice_id)

    if existing_record and duplicate_strategy == "skip":
        res = existing_record.to_dict()
        res["import_status"] = "skipped"
        return res

    # Store XML file to data/invoices_xml/
    safe_filename = os.path.basename(filename)
    xml_path = os.path.join(XML_DIR, safe_filename)
    with open(xml_path, "wb") as f:
        f.write(xml_bytes)

    # Run audits (passing list of other invoices as dictionaries)
    other_invoices = [item.to_dict() for item in Invoice.query.all()]
    warnings = _run_smart_audits(parsed_invoice, other_invoices)

    if not schema_valid:
        warnings.append(f"Cấu trúc XSD: {schema_err}")

    # Generate signature warning messages for UI if not blocked
    if parsed_invoice.get("has_signature"):
        if not sig_details["sig_verified"]:
            err_msg = sig_details.get("sig_error") or "Chữ ký số không hợp lệ."
            warnings.append(f"Chữ ký số: {err_msg}")
        elif sig_details.get("sig_error"):
            warnings.append(f"Chữ ký số: {sig_details['sig_error']}")
        
        # Check node-level cryptographic tampering
        if sig_details.get("sig_tampered_nodes"):
            for node_uri in sig_details["sig_tampered_nodes"]:
                warnings.append(f"CRITICAL_SIGNATURE_TAMPER: Đối tượng XML ({node_uri}) đã bị chỉnh sửa sau khi ký số.")
    else:
        warnings.append("Hóa đơn không có chữ ký số hợp lệ.")



    # If it exists and strategy is overwrite, delete it first to ensure clean state (cascade deletes old items)
    if existing_record:
        db.session.delete(existing_record)
        db.session.commit()

    # Determine taxpayer_mst
    if not taxpayer_mst:
        buyer_mst = parsed_invoice.get("buyer_mst")
        seller_mst = parsed_invoice.get("seller_mst")
        from invoices.models import TaxpayerProfile
        # Check if buyer_mst is a registered taxpayer
        if buyer_mst and db.session.get(TaxpayerProfile, buyer_mst):
            taxpayer_mst = buyer_mst
        # Else check if seller_mst is a registered taxpayer
        elif seller_mst and db.session.get(TaxpayerProfile, seller_mst):
            taxpayer_mst = seller_mst
        else:
            from flask import current_app
            taxpayer_mst = current_app.config.get("CURRENT_TAXPAYER_MST")

    # Create new stored structure
    invoice_record = Invoice(
        id=invoice_id,
        filename=safe_filename,
        invoice_type=parsed_invoice["invoice_type"],
        template_code=parsed_invoice["template_code"],
        symbol=parsed_invoice["symbol"],
        number=parsed_invoice["number"],
        date=parsed_invoice["date"],
        currency=parsed_invoice["currency"],
        seller_name=parsed_invoice["seller_name"],
        seller_mst=parsed_invoice["seller_mst"],
        seller_address=parsed_invoice["seller_address"],
        seller_phone=parsed_invoice["seller_phone"],
        buyer_name=parsed_invoice["buyer_name"],
        buyer_mst=parsed_invoice["buyer_mst"],
        buyer_address=parsed_invoice["buyer_address"],
        amount_before_tax=parsed_invoice["amount_before_tax"],
        tax_amount=parsed_invoice["tax_amount"],
        total_amount=parsed_invoice["total_amount"],
        has_signature=parsed_invoice["has_signature"],
        signing_date=parsed_invoice.get("signing_date"),
        payment_method=parsed_invoice.get("payment_method", ""),
        is_cancelled=parsed_invoice.get("is_cancelled", False),
        cancellation_date=parsed_invoice.get("cancellation_date"),
        cancellation_reason=parsed_invoice.get("cancellation_reason"),
        imported_at=datetime.now().isoformat(),
        import_status="XSD_VALIDATION_FAILED" if not schema_valid else ("overwritten" if existing_record else "imported"),
        taxpayer_mst=taxpayer_mst
    )
    invoice_record.signature_details = sig_details
    invoice_record.warnings = warnings
    db.session.add(invoice_record)

    for item_data in parsed_invoice.get("items", []):
        item = LineItem(
            invoice_id=invoice_id,
            item_name=item_data["item_name"],
            unit=item_data.get("unit"),
            quantity=item_data.get("quantity", 0.0),
            unit_price=item_data.get("unit_price", 0.0),
            amount_before_tax=item_data.get("amount_before_tax", 0.0),
            tax_rate=item_data.get("tax_rate", "0%"),
            tax_amount=item_data.get("tax_amount", 0.0)
        )
        db.session.add(item)

    # Calculate T-Score and rating before saving
    calculate_invoice_t_score(invoice_record)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Database error during import_xml_invoice: {str(e)}")

    # Dispatch downloaded webhook event
    try:
        from invoices.erp_service import WebhookDispatcher
        WebhookDispatcher.dispatch_event("invoice.downloaded", invoice_record.to_dict())
    except Exception as we:
        import logging
        logging.getLogger(__name__).warning(f"Webhook dispatch failed: {we}")

    # Run AI compliance audit automatically if enabled
    try:
        from invoices.scheduler import load_scheduler_settings
        settings = load_scheduler_settings()
        if settings.get("ai_enabled"):
            from invoices.ai_service import AIComplianceAuditor
            auditor = AIComplianceAuditor()
            auditor.audit_invoice(invoice_record)
            
            # Dispatch audited webhook event
            try:
                from invoices.erp_service import WebhookDispatcher
                WebhookDispatcher.dispatch_event("invoice.audited", invoice_record.to_dict())
            except Exception as we:
                pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"AI compliance audit failed during upload: {e}")

    # Run Cloud Sync automatically if enabled
    try:
        from invoices.cloud_service import CloudSyncService
        sync_service = CloudSyncService()
        
        pdf_bytes = None
        try:
            from flask import render_template
            from invoices.routes import render_html_to_pdf
            from invoices.service import doc_so_tien_vietnam
            
            line_items = [item.to_dict() for item in invoice_record.items]
            sum_before_tax = sum(item.get("amount_before_tax", 0.0) for item in line_items)
            sum_tax = sum(item.get("tax_amount", 0.0) for item in line_items)
            total_payable = sum_before_tax + sum_tax
            total_payable_words = doc_so_tien_vietnam(total_payable)
            
            user_company = {
                "name": "CONG TY CO PHAN CONG NGHE GDT INVOICE HUB",
                "mst": "0109999999",
                "address": "Toa nha Technopark, Gia Lam, TP. Ha Noi",
                "phone": "1900 8888",
            }
            
            seller = {
                "name": invoice_record.seller_name or "",
                "mst": invoice_record.seller_mst or "",
                "address": invoice_record.seller_address or "",
                "phone": invoice_record.seller_phone or "",
            }
            buyer = {
                "name": invoice_record.buyer_name or "",
                "mst": invoice_record.buyer_mst or "",
                "address": invoice_record.buyer_address or "",
            }
            
            html_content = render_template(
                "invoice_pdf_export.html",
                invoice=invoice_record.to_dict(),
                line_items=line_items,
                seller=seller,
                buyer=buyer,
                sum_before_tax=sum_before_tax,
                sum_tax=sum_tax,
                total_payable=total_payable,
                total_payable_words=total_payable_words
            )
            pdf_stream = render_html_to_pdf(html_content)
            pdf_bytes = pdf_stream.getvalue()
        except Exception as pe:
            import logging
            logging.getLogger(__name__).warning(f"Failed to generate PDF for cloud sync: {pe}")
            
        sync_service.sync_invoice_to_cloud(invoice_record.id, xml_bytes, pdf_bytes)
    except Exception as se:
        import logging
        logging.getLogger(__name__).warning(f"Cloud sync failed during import: {se}")

    # Run ERP Auto-posting automatically if enabled
    try:
        from invoices.erp_service import post_invoice_to_erp
        post_invoice_to_erp(invoice_record)
    except Exception as erpe:
        import logging
        logging.getLogger(__name__).warning(f"ERP auto-post failed during import: {erpe}")

    return invoice_record.to_dict()





def search_local_items(query: str, taxpayer_mst: str = None) -> list[dict]:
    """Search for items in all locally stored invoices matching the query, optionally filtering by taxpayer_mst."""

    if not query:
        return []

    query_lower = query.lower().strip()
    invoices = get_local_invoices(taxpayer_mst)
    results = []

    for inv in invoices:
        for item in inv.get("items", []):
            if query_lower in item.get("item_name", "").lower():
                results.append({
                    "item_name": item["item_name"],
                    "unit": item.get("unit", ""),
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "amount_before_tax": item["amount_before_tax"],
                    "tax_rate": item["tax_rate"],
                    "tax_amount": item["tax_amount"],
                    "invoice_id": inv["id"],
                    "invoice_number": inv["number"],
                    "invoice_date": inv["date"],
                    "seller_name": inv["seller_name"],
                    "seller_mst": inv["seller_mst"],
                })
    return results


def delete_local_invoice(invoice_id: str) -> bool:
    """
    Delete a single local invoice by ID, including its XML file from data/invoices_xml/.
    Returns True if deleted, False if not found.
    """
    from extensions import db
    from invoices.models import Invoice

    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        return False

    # Remove XML file if exists
    filename = invoice.filename
    if filename:
        xml_path = os.path.join(XML_DIR, filename)
        if os.path.exists(xml_path):
            try:
                os.remove(xml_path)
            except Exception:
                pass

    try:
        db.session.delete(invoice)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def adjust_local_invoice(invoice_id: str, adjust_data: dict) -> dict:
    """
    Adjust key fields of a local invoice, re-run smart audits, and save.
    Returns the updated invoice record or raises ValueError if not found.
    """
    from extensions import db
    from invoices.models import Invoice

    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Không tìm thấy hóa đơn ID {invoice_id} để điều chỉnh.")

    # Update allowed fields
    if "date" in adjust_data:
        invoice.date = str(adjust_data["date"])
    if "seller_name" in adjust_data:
        invoice.seller_name = str(adjust_data["seller_name"])
    if "seller_mst" in adjust_data:
        invoice.seller_mst = str(adjust_data["seller_mst"])
    if "buyer_name" in adjust_data:
        invoice.buyer_name = str(adjust_data["buyer_name"])
    if "buyer_mst" in adjust_data:
        invoice.buyer_mst = str(adjust_data["buyer_mst"])
    if "amount_before_tax" in adjust_data:
        invoice.amount_before_tax = float(adjust_data["amount_before_tax"])
    if "tax_amount" in adjust_data:
        invoice.tax_amount = float(adjust_data["tax_amount"])
    if "total_amount" in adjust_data:
        invoice.total_amount = float(adjust_data["total_amount"])
    if "payment_method" in adjust_data:
        invoice.payment_method = str(adjust_data["payment_method"])
    if "invoice_status" in adjust_data:
        invoice.invoice_status = str(adjust_data["invoice_status"])
    if "notes" in adjust_data:
        invoice.notes = str(adjust_data["notes"])

    # Re-run audits with the rest of database (excluding itself for duplicate checks)
    other_db = [item.to_dict() for item in Invoice.query.filter(Invoice.id != invoice_id).all()]
    invoice_dict = invoice.to_dict()
    warnings = _run_smart_audits(invoice_dict, other_db)

    invoice.warnings = warnings
    invoice.updated_at = datetime.now().isoformat()
    
    # Calculate T-Score and rating before saving adjustments
    calculate_invoice_t_score(invoice)

    try:
        db.session.commit()
        return invoice.to_dict()
    except Exception:
        db.session.rollback()
        raise



def batch_download_invoices(month: str, direction: str, on_progress=None, duplicate_strategy: str = "overwrite") -> bytes:
    """
    Fetch all invoices for the given month from GDT, save them to local,
    parse & run smart audits, and package them into a ZIP archive bytes.
    Supports progress updates via an optional on_progress callback.
    """

    try:
        # Month format: YYYY-MM
        year_val, month_val = map(int, month.split("-"))
        date_from = date(year_val, month_val, 1)
        import calendar
        last_day = calendar.monthrange(year_val, month_val)[1]
        date_to = date(year_val, month_val, last_day)
    except Exception as e:
        if on_progress:
            on_progress(0, 0, "failed", error=f"Định dạng tháng không hợp lệ: {str(e)}")
        raise ValueError(f"Dinh dang thang khong hop le: {str(e)}")

    query = InvoiceQuery(date_from=date_from, date_to=date_to, cancelled_only=False, direction=direction)
    invoices = fetch_invoices(query)
    total = len(invoices)

    imported = 0
    skipped = 0
    overwritten = 0
    failed = 0

    if on_progress:
        on_progress(0, total, "running", imported=imported, skipped=skipped, overwritten=overwritten, failed=failed)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for idx, inv in enumerate(invoices):
            invoice_id = inv["id"]
            try:
                from extensions import db
                from invoices.models import Invoice

                xml_bytes = None
                filename = f"GDT_{inv.get('issuer', 'NB').replace(' ', '_')}_{inv['date']}_{invoice_id}.xml"

                # Optimization: check local cache first if strategy is "skip"
                if duplicate_strategy == "skip":
                    existing_invoice = db.session.get(Invoice, invoice_id)
                    if existing_invoice and existing_invoice.filename:
                        xml_path = os.path.join(XML_DIR, existing_invoice.filename)
                        if os.path.exists(xml_path):
                            try:
                                with open(xml_path, "rb") as f:
                                    xml_bytes = f.read()
                                filename = existing_invoice.filename
                            except Exception:
                                pass

                # Fallback to downloading if not cached or read failed
                if xml_bytes is None:
                    xml_bytes = download_invoice_xml(invoice_id)

                zip_file.writestr(filename, xml_bytes)

                # Automatically import into local database
                res = import_xml_invoice(xml_bytes, filename, duplicate_strategy=duplicate_strategy)
                status = res.get("import_status", "imported")
                if status == "skipped":
                    skipped += 1
                elif status == "overwritten":
                    overwritten += 1
                else:
                    imported += 1
            except Exception as e:
                failed += 1
            finally:
                if on_progress:
                    on_progress(idx + 1, total, "running", imported=imported, skipped=skipped, overwritten=overwritten, failed=failed)

    zip_bytes = zip_buffer.getvalue()
    if on_progress:
        on_progress(total, total, "completed", zip_bytes=zip_bytes, imported=imported, skipped=skipped, overwritten=overwritten, failed=failed)
    return zip_bytes


def doc_so_tien_vietnam(number: float) -> str:
    """Convert a number into Vietnamese words."""
    try:
        val = int(round(number))
    except (ValueError, TypeError):
        return "Không đồng"

    if val == 0:
        return "Không đồng"

    don_vi = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    hang = ["", "nghìn", "triệu", "tỷ"]

    def doc_block(n: int, is_first: bool) -> str:
        hundreds = n // 100
        tens = (n % 100) // 10
        ones = n % 10

        res = []
        if hundreds > 0 or not is_first:
            res.append(don_vi[hundreds] + " trăm")

        if tens > 0:
            if tens == 1:
                res.append("mười")
            else:
                res.append(don_vi[tens] + " mươi")
        elif hundreds > 0 or not is_first:
            if ones > 0:
                res.append("lẻ")

        if ones > 0:
            if ones == 1 and tens > 1:
                res.append("mốt")
            elif ones == 5 and tens > 0:
                res.append("lăm")
            else:
                res.append(don_vi[ones])

        return " ".join(res)

    blocks = []
    temp = val
    while temp > 0:
        blocks.append(temp % 1000)
        temp //= 1000

    words = []
    for i in range(len(blocks) - 1, -1, -1):
        block_val = blocks[i]
        if block_val == 0:
            continue
        
        is_first_block = (i == len(blocks) - 1)
        block_text = doc_block(block_val, is_first_block)
        
        actual_scale = []
        temp_i = i
        while temp_i > 0:
            if temp_i >= 3:
                actual_scale.append("tỷ")
                temp_i -= 3
            elif temp_i == 2:
                actual_scale.append("triệu")
                temp_i = 0
            elif temp_i == 1:
                actual_scale.append("nghìn")
                temp_i = 0
        
        scale_text = " ".join(actual_scale)
        words.append(block_text)
        if scale_text:
            words.append(scale_text)

    text = " ".join(words).strip()
    text = " ".join(text.split())
    if text:
        text = text[0].upper() + text[1:] + " đồng chẵn"
    else:
        text = "Không đồng"
        
    return text



