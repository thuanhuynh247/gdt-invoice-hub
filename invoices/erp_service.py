"""ERP Connectors (MISA & Odoo) and Webhook Hub for Sprint 3.2.

Provides Excel/CSV export templates for MISA/Odoo and a secure Webhook Dispatcher
with HMAC-SHA256 payload signing.
"""

from __future__ import annotations

import io
import csv
import hmac
import hashlib
import json
import logging
import requests
from flask import current_app
from openpyxl import Workbook
from export.formatter import format_header_row, auto_adjust_column_widths

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from invoices.models import Invoice

logger = logging.getLogger(__name__)

# Thread-safe global for capturing sent webhooks in testing
MOCK_SENT_WEBHOOKS = []

def generate_misa_export(invoices: list[Invoice]) -> bytes:
    """Build a MISA SME compatible Excel workbook for importing purchase documents."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "MISA SME Purchase Invoices"

    headers = [
        "Ngày hạch toán",
        "Ngày chứng từ",
        "Số chứng từ",
        "Mã số thuế người bán",
        "Tên người bán",
        "Địa chỉ người bán",
        "Diễn giải",
        "Tài khoản Nợ",
        "Tài khoản Có",
        "Số tiền trước thuế",
        "Thuế suất",
        "Tiền thuế",
        "Tổng thanh toán",
        "Phương thức thanh toán"
    ]
    worksheet.append(headers)
    format_header_row(worksheet)

    for inv in invoices:
        # Determine posting date
        inv_date = inv.date or ""
        try:
            # Reformat to DD/MM/YYYY for MISA
            from datetime import datetime
            dt = datetime.strptime(inv_date, "%Y-%m-%d")
            display_date = dt.strftime("%d/%m/%Y")
        except Exception:
            display_date = inv_date

        doc_num = f"{inv.symbol or ''}/{inv.number or ''}"
        
        # Simple account detection based on payment method
        debit_acc = "1561"  # Default Merchandise Inventory
        credit_acc = "331"  # Default Accounts Payable
        
        payment_method_lower = (inv.payment_method or "").lower()
        if "tiền mặt" in payment_method_lower or "tm" in payment_method_lower:
            credit_acc = "1111"  # Cash
        elif "chuyển khoản" in payment_method_lower or "ck" in payment_method_lower:
            credit_acc = "1121"  # Bank

        # Detect expense type if categorized (mock detection or category column)
        # Let's check first item category if available
        if inv.items:
            category = (inv.items[0].expense_category or "").lower()
            if "văn phòng phẩm" in category or "dịch vụ" in category:
                debit_acc = "6422"  # Admin Expense

        row = [
            display_date,
            display_date,
            doc_num,
            inv.seller_mst or "",
            inv.seller_name or "",
            inv.seller_address or "",
            f"Mua hàng theo HĐ số {inv.number or ''} từ {inv.seller_name or ''}",
            debit_acc,
            credit_acc,
            inv.amount_before_tax,
            "10%",  # standard default tax rate representation
            inv.tax_amount,
            inv.total_amount,
            inv.payment_method or ""
        ]
        worksheet.append(row)

    # Number formats
    for col_idx in [10, 12, 13]:
        for row in worksheet.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                cell.number_format = '#,##0'

    auto_adjust_column_widths(worksheet)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()


def generate_odoo_export(invoices: list[Invoice]) -> str:
    """Build an Odoo Journal Entries CSV template."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)

    # Odoo journal entry CSV headers
    writer.writerow([
        "ref",
        "date",
        "journal_id",
        "line_ids/account_id",
        "line_ids/name",
        "line_ids/debit",
        "line_ids/credit"
    ])

    for inv in invoices:
        ref = f"INV-{inv.number or ''}"
        date = inv.date or ""
        journal = "Purchase Journal"
        
        # Account mappings
        expense_acc = "642000"
        payable_acc = "331000"
        vat_acc = "133100"
        
        payment_method_lower = (inv.payment_method or "").lower()
        if "tiền mặt" in payment_method_lower or "tm" in payment_method_lower:
            payable_acc = "111100"
        elif "chuyển khoản" in payment_method_lower or "ck" in payment_method_lower:
            payable_acc = "112100"

        # Item description
        desc = f"Mua hàng từ {inv.seller_name or 'Đầu vào'}"

        # 1. Line item: Expense debit
        writer.writerow([
            ref,
            date,
            journal,
            expense_acc,
            desc,
            inv.amount_before_tax,
            0.0
        ])
        
        # 2. Line item: VAT debit (if tax present)
        if inv.tax_amount > 0:
            writer.writerow([
                "",
                "",
                "",
                vat_acc,
                f"Thuế GTGT HĐ {inv.number or ''}",
                inv.tax_amount,
                0.0
            ])

        # 3. Line item: Payable credit
        writer.writerow([
            "",
            "",
            "",
            payable_acc,
            desc,
            0.0,
            inv.total_amount
        ])

    return output.getvalue()


class WebhookDispatcher:
    """Dispatches webhook events with secure HMAC-SHA256 signature signing."""

    @staticmethod
    def dispatch_event(event_type: str, data: dict) -> bool:
        """Sign and POST payload to configured webhook URL."""
        from invoices.scheduler import load_scheduler_settings

        # Check for testing mode
        testing_mode = False
        try:
            if current_app and current_app.config.get("TESTING"):
                testing_mode = True
        except Exception:
            pass

        settings = load_scheduler_settings()
        enabled = settings.get("webhook_enabled", False)
        webhook_url = settings.get("webhook_url", "")
        secret = settings.get("webhook_secret", "")

        # Always support testing capture
        if testing_mode:
            MOCK_SENT_WEBHOOKS.append({
                "event_type": event_type,
                "data": data,
                "webhook_url": webhook_url
            })
            logger.info(f"[MOCK WEBHOOK] Dispatched event {event_type}")
            return True

        if not enabled or not webhook_url:
            return False

        payload = {
            "event": event_type,
            "data": data
        }
        payload_str = json.dumps(payload, ensure_ascii=False)

        # Signature computation
        signature = ""
        if secret:
            signature = hmac.new(
                secret.encode("utf-8"),
                payload_str.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-GDT-Signature": signature
        }

        try:
            resp = requests.post(webhook_url, headers=headers, data=payload_str, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to deliver webhook event {event_type} to {webhook_url}: {e}")
            return False


# Thread-safe global for capturing sent ERP postings in testing
MOCK_ERP_POSTS = []


def post_invoice_to_erp(invoice: Invoice) -> bool:
    """Post double-entry ledger entries for the invoice directly to the configured ERP system (MISA or Odoo)."""
    from invoices.scheduler import load_scheduler_settings
    from extensions import db
    from datetime import datetime

    # Check for testing mode
    testing_mode = False
    try:
        if current_app and current_app.config.get("TESTING"):
            testing_mode = True
    except Exception:
        pass

    settings = load_scheduler_settings()
    erp_enabled = settings.get("erp_enabled", False)
    erp_type = settings.get("erp_type", "none")
    erp_api_url = settings.get("erp_api_url", "")
    erp_auth_token = settings.get("erp_auth_token", "")

    # Decrypt token if encrypted
    if erp_auth_token:
        try:
            from auth.crypto import decrypt_password
            if erp_auth_token.startswith("gAAAAA"):
                erp_auth_token = decrypt_password(erp_auth_token)
        except Exception:
            pass

    if not erp_enabled or erp_type == "none" or not erp_api_url:
        return False

    # Account detection matching export logic
    debit_acc = "1561" if erp_type == "misa" else "642000"
    credit_acc = "331" if erp_type == "misa" else "331000"
    vat_acc = "133" if erp_type == "misa" else "133100"

    payment_method_lower = (invoice.payment_method or "").lower()
    if "tiền mặt" in payment_method_lower or "tm" in payment_method_lower:
        credit_acc = "1111" if erp_type == "misa" else "111100"
    elif "chuyển khoản" in payment_method_lower or "ck" in payment_method_lower:
        credit_acc = "1121" if erp_type == "misa" else "112100"

    if invoice.items:
        category = (invoice.items[0].expense_category or "").lower()
        if "văn phòng phẩm" in category or "dịch vụ" in category:
            debit_acc = "6422" if erp_type == "misa" else "642000"

    # Construct specific ERP payload
    payload = {}
    if erp_type == "misa":
        payload = {
            "RefDate": invoice.date,
            "PostedDate": datetime.now().strftime("%Y-%m-%d"),
            "RefNo": f"{invoice.symbol}/{invoice.number}",
            "SellerMST": invoice.seller_mst or "",
            "SellerName": invoice.seller_name or "",
            "Description": f"Mua hàng theo HĐ số {invoice.number or ''}",
            "DebitAccount": debit_acc,
            "CreditAccount": credit_acc,
            "VatAccount": vat_acc,
            "AmountBeforeTax": invoice.amount_before_tax,
            "VatAmount": invoice.tax_amount,
            "TotalAmount": invoice.total_amount,
            "PaymentMethod": invoice.payment_method or ""
        }
    elif erp_type == "odoo":
        # Formulate a journal entry matching Odoo structure
        payload = {
            "ref": f"INV-{invoice.number or ''}",
            "date": invoice.date or datetime.now().strftime("%Y-%m-%d"),
            "journal_id": "Purchase Journal",
            "line_ids": [
                {
                    "account_id": debit_acc,
                    "name": f"Expense - {invoice.seller_name or ''}",
                    "debit": invoice.amount_before_tax,
                    "credit": 0.0
                },
                {
                    "account_id": vat_acc,
                    "name": f"VAT - HĐ {invoice.number or ''}",
                    "debit": invoice.tax_amount,
                    "credit": 0.0
                },
                {
                    "account_id": credit_acc,
                    "name": f"Payable - {invoice.seller_name or ''}",
                    "debit": 0.0,
                    "credit": invoice.total_amount
                }
            ]
        }

    # If testing mode, capture and return success
    if testing_mode:
        MOCK_ERP_POSTS.append({
            "erp_type": erp_type,
            "url": erp_api_url,
            "payload": payload,
            "invoice_id": invoice.id
        })
        invoice.erp_synced = True
        invoice.erp_sync_date = datetime.now().isoformat()
        invoice.erp_sync_error = None
        db.session.commit()
        logger.info(f"[MOCK ERP] Dispatched ledger entry to {erp_type} at {erp_api_url}")
        return True

    headers = {
        "Content-Type": "application/json",
    }
    if erp_auth_token:
        headers["Authorization"] = f"Bearer {erp_auth_token}"

    try:
        resp = requests.post(erp_api_url, headers=headers, json=payload, timeout=10)
        if resp.status_code in (200, 201):
            invoice.erp_synced = True
            invoice.erp_sync_date = datetime.now().isoformat()
            invoice.erp_sync_error = None
            db.session.commit()
            return True
        else:
            invoice.erp_synced = False
            invoice.erp_sync_error = f"ERP returned status {resp.status_code}: {resp.text}"
            db.session.commit()
            return False
    except Exception as e:
        invoice.erp_synced = False
        invoice.erp_sync_error = str(e)
        db.session.commit()
        return False
