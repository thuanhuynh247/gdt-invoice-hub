"""Utilities for date validation and response normalization."""

from __future__ import annotations

from datetime import date, datetime


class DateValidationError(ValueError):
    """Raised when a date range is missing or invalid."""


def validate_date_range(date_from: str, date_to: str) -> tuple[date, date]:
    """Validate date range strings and return parsed date objects."""

    if not date_from or not date_to:
        raise DateValidationError("Ban phai nhap ca tu ngay va den ngay.")

    try:
        parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError as error:
        raise DateValidationError("Ngay phai dung dinh dang YYYY-MM-DD.") from error

    if parsed_from > parsed_to:
        raise DateValidationError("Tu ngay phai nho hon hoac bang den ngay.")

    if parsed_from > date.today() or parsed_to > date.today():
        raise DateValidationError("Khong duoc tim hoa don trong tuong lai.")

    return parsed_from, parsed_to


import xml.etree.ElementTree as ET


def normalize_invoice(raw_invoice: dict) -> dict:
    """Map a raw invoice payload into the UI/API shape required by the spec."""

    return {
        "id": raw_invoice["id"],
        "date": raw_invoice["date"],
        "amount": raw_invoice["amount"],
        "status": raw_invoice["status"],
        "issuer": raw_invoice["issuer"],
        "description": raw_invoice.get("description", ""),
        "is_cancelled": raw_invoice.get("is_cancelled", False),
        "cancellation_date": raw_invoice.get("cancellation_date"),
        "cancellation_reason": raw_invoice.get("cancellation_reason"),
        "line_items": raw_invoice.get("line_items", []),
    }


def parse_xml_line_items(xml_bytes: bytes) -> list[dict]:
    """Parse nested line items from a raw GDT XML invoice."""

    try:
        root = ET.fromstring(xml_bytes)
        # Strip XML namespaces for easier XPath searching
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        line_items = []
        for hhdvu in root.findall(".//HHDVu"):
            item_name = hhdvu.findtext("Ten") or hhdvu.findtext("TChat") or ""
            if not item_name.strip():
                continue

            quantity_text = hhdvu.findtext("SLuong") or "0"
            price_text = hhdvu.findtext("DGia") or "0"
            amount_text = hhdvu.findtext("ThTien") or "0"
            tax_rate = hhdvu.findtext("TSuat") or "0%"
            tax_amount_text = hhdvu.findtext("TThue") or "0"

            try:
                quantity = float(quantity_text.replace(",", ""))
                unit_price = float(price_text.replace(",", ""))
                amount_before_tax = float(amount_text.replace(",", ""))
                tax_amount = float(tax_amount_text.replace(",", ""))
            except ValueError:
                quantity = 0.0
                unit_price = 0.0
                amount_before_tax = 0.0
                tax_amount = 0.0

            line_items.append(
                {
                    "item_name": item_name.strip(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "amount_before_tax": amount_before_tax,
                    "tax_rate": tax_rate.strip(),
                    "tax_amount": tax_amount,
                }
            )
        return line_items
    except Exception:
        return []


def parse_complete_xml(xml_bytes: bytes) -> dict:
    """Parse all detailed fields and line items from a GDT standard XML invoice."""

    try:
        root = ET.fromstring(xml_bytes)
        # Strip XML namespaces for easier XPath searching
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        # Extract general info
        title = root.findtext(".//THDon") or root.findtext(".//tenHDon") or "Hóa đơn giá trị gia tăng"
        template = root.findtext(".//KHMSHDon") or root.findtext(".//khmshdon") or "1"
        symbol = root.findtext(".//KHHDon") or root.findtext(".//khhdon") or "C26TBA"

        # Number: pad with zeros to make it 8 digits if it's a numeric string less than 8 digits
        number_raw = root.findtext(".//SHDon") or root.findtext(".//shdon") or "00000000"
        try:
            number = f"{int(number_raw):08d}"
        except ValueError:
            number = number_raw

        # Date: try multiple formats
        date_raw = root.findtext(".//NLap") or root.findtext(".//ngay") or ""
        invoice_date = ""
        if date_raw:
            try:
                # E.g. 2026-05-21T10:00:00 or 2026-05-21
                invoice_date = date_raw.split("T")[0]
            except Exception:
                invoice_date = date_raw
        if not invoice_date:
            invoice_date = date.today().isoformat()

        currency = root.findtext(".//DVTTe") or root.findtext(".//dvtte") or "VND"
        payment_method = root.findtext(".//HTTToan") or root.findtext(".//htttoan") or ""

        # Seller
        seller_node = root.find(".//NBan")
        if seller_node is None:
            seller_node = root.find(".//nban")
        seller_name = ""
        seller_mst = ""
        seller_address = ""
        seller_phone = ""
        if seller_node is not None:
            seller_name = seller_node.findtext("Ten") or seller_node.findtext("ten") or ""
            seller_mst = seller_node.findtext("MST") or seller_node.findtext("mst") or ""
            seller_address = seller_node.findtext("DChi") or seller_node.findtext("dchi") or ""
            seller_phone = seller_node.findtext("SDThoai") or seller_node.findtext("sdt") or ""

        # Buyer
        buyer_node = root.find(".//NMua")
        if buyer_node is None:
            buyer_node = root.find(".//nmua")
        buyer_name = ""
        buyer_mst = ""
        buyer_address = ""
        if buyer_node is not None:
            buyer_name = buyer_node.findtext("TenDonVi") or buyer_node.findtext("tenDonVi") or buyer_node.findtext("Ten") or buyer_node.findtext("ten") or ""
            buyer_mst = buyer_node.findtext("MST") or buyer_node.findtext("mst") or ""
            buyer_address = buyer_node.findtext("DChi") or buyer_node.findtext("dchi") or ""

        # Financial totals
        amount_before_tax_text = root.findtext(".//TgTCThue") or root.findtext(".//tgtcThue") or "0"
        tax_amount_text = root.findtext(".//TgTThue") or root.findtext(".//tgtThue") or "0"
        total_amount_text = root.findtext(".//TgTTTBSo") or root.findtext(".//tgtttbSo") or "0"

        try:
            amount_before_tax = float(amount_before_tax_text.replace(",", ""))
            tax_amount = float(tax_amount_text.replace(",", ""))
            total_amount = float(total_amount_text.replace(",", ""))
        except ValueError:
            amount_before_tax = 0.0
            tax_amount = 0.0
            total_amount = 0.0

        # Items
        items = []
        for hhdvu in root.findall(".//HHDVu"):
            item_name = hhdvu.findtext("Ten") or hhdvu.findtext("ten") or hhdvu.findtext("TChat") or ""
            if not item_name.strip():
                continue

            unit = hhdvu.findtext("DVT") or hhdvu.findtext("dvt") or ""
            quantity_text = hhdvu.findtext("SLuong") or "0"
            price_text = hhdvu.findtext("DGia") or "0"
            amount_text = hhdvu.findtext("ThTien") or "0"
            tax_rate = hhdvu.findtext("TSuat") or "10%"
            item_tax_amount_text = hhdvu.findtext("TThue") or "0"

            try:
                quantity = float(quantity_text.replace(",", ""))
                unit_price = float(price_text.replace(",", ""))
                item_amount_before_tax = float(amount_text.replace(",", ""))
                item_tax_amount = float(item_tax_amount_text.replace(",", ""))
            except ValueError:
                quantity = 0.0
                unit_price = 0.0
                item_amount_before_tax = 0.0
                item_tax_amount = 0.0

            items.append({
                "item_name": item_name.strip(),
                "unit": unit.strip(),
                "quantity": quantity,
                "unit_price": unit_price,
                "amount_before_tax": item_amount_before_tax,
                "tax_rate": tax_rate.strip(),
                "tax_amount": item_tax_amount
            })

        # fallbacks
        if amount_before_tax == 0.0 and items:
            amount_before_tax = sum(item["amount_before_tax"] for item in items)
        if tax_amount == 0.0 and items:
            tax_amount = sum(item["tax_amount"] for item in items)
        if total_amount == 0.0:
            total_amount = amount_before_tax + tax_amount

        # Signature
        has_signature = root.find(".//Signature") is not None or root.find(".//SignatureValue") is not None

        # Try to parse signing date (NgayKy, SigningTime, etc.)
        signing_date_raw = None
        for tag in [".//SigningTime", ".//signingTime", ".//NgayKy", ".//ngayKy", ".//NgayKyHDon"]:
            node = root.find(tag)
            if node is not None and node.text:
                signing_date_raw = node.text.strip()
                break

        signing_date = None
        if signing_date_raw:
            try:
                # E.g. "2026-05-22T10:00:00" or "2026-05-22" or "2026/05/22"
                # Strip time part if present
                clean_date = signing_date_raw.split("T")[0].replace("/", "-")
                # Ensure it fits YYYY-MM-DD
                datetime.strptime(clean_date[:10], "%Y-%m-%d")
                signing_date = clean_date[:10]
            except Exception:
                pass

        return {
            "invoice_type": title.strip(),
            "template_code": template.strip(),
            "symbol": symbol.strip(),
            "number": number.strip(),
            "date": invoice_date,
            "currency": currency.strip(),
            "seller_name": seller_name.strip(),
            "seller_mst": seller_mst.strip(),
            "seller_address": seller_address.strip(),
            "seller_phone": seller_phone.strip(),
            "buyer_name": buyer_name.strip(),
            "buyer_mst": buyer_mst.strip(),
            "buyer_address": buyer_address.strip(),
            "amount_before_tax": amount_before_tax,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "items": items,
            "has_signature": has_signature,
            "signing_date": signing_date,
            "payment_method": payment_method.strip()
        }
    except Exception as error:
        raise ValueError(f"Loi cu phap tep XML: {str(error)}")

