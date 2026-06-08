"""Customs XML Declaration Parser & Import VAT Reconciler (US-334, US-335)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from extensions import db
from invoices.models import CustomsDeclaration, Invoice


def parse_customs_xml(xml_bytes: bytes) -> dict:
    """Parses a VNACCS/VCIS Customs XML import declaration.

    Extracts declaration number, dates, duties, value, and HS codes.
    """
    root = ET.fromstring(xml_bytes)

    # Simple namespace-agnostic search
    def find_text(tag_name: str, default: str = "") -> str:
        for elem in root.iter():
            if elem.tag.endswith(tag_name):
                return (elem.text or "").strip()
        return default

    declaration_number = find_text("DeclarationNo") or find_text("DeclarationNumber")
    declaration_date = find_text("DeclarationDate")
    taxpayer_mst = find_text("ImporterMST") or find_text("TaxCode")

    customs_value_vnd = float(find_text("CustomsValueVND") or find_text("CustomsValue") or "0")
    import_duty_vnd = float(find_text("ImportDutyVND") or find_text("ImportDuty") or "0")
    import_vat_vnd = float(find_text("ImportVATVND") or find_text("ImportVAT") or "0")

    exchange_rate = float(find_text("ExchangeRate") or "1.0")
    currency = find_text("CurrencyCode") or find_text("Currency") or "VND"

    # Collect HS Codes
    hs_codes = []
    for elem in root.iter():
        if elem.tag.endswith("HSCode") and elem.text:
            hs_codes.append(elem.text.strip())

    if not declaration_number:
        raise ValueError("Invalid customs declaration XML: missing DeclarationNo/DeclarationNumber.")

    return {
        "declaration_number": declaration_number,
        "declaration_date": declaration_date or "2026-06-03",
        "taxpayer_mst": taxpayer_mst or "0101234567",
        "customs_value_vnd": customs_value_vnd,
        "import_duty_vnd": import_duty_vnd,
        "import_vat_vnd": import_vat_vnd,
        "exchange_rate": exchange_rate,
        "currency": currency,
        "hs_codes": hs_codes,
        "xml_content": xml_bytes.decode("utf-8", errors="ignore")
    }


class CustomsReconciliationEngine:
    """Reconciles customs import declarations with input VAT invoices to detect variances."""

    @staticmethod
    def ingest_declaration(xml_bytes: bytes) -> CustomsDeclaration:
        """Parses and stores a customs declaration in the database."""
        data = parse_customs_xml(xml_bytes)
        decl = CustomsDeclaration.query.filter_by(declaration_number=data["declaration_number"]).first()

        if not decl:
            decl = CustomsDeclaration(declaration_number=data["declaration_number"])
            db.session.add(decl)

        decl.declaration_date = data["declaration_date"]
        decl.taxpayer_mst = data["taxpayer_mst"]
        decl.customs_value_vnd = data["customs_value_vnd"]
        decl.import_duty_vnd = data["import_duty_vnd"]
        decl.import_vat_vnd = data["import_vat_vnd"]
        decl.exchange_rate = data["exchange_rate"]
        decl.currency = data["currency"]
        decl.hs_codes = data["hs_codes"]
        decl.xml_content = data["xml_content"]
        decl.status = "unreconciled"

        db.session.commit()
        return decl

    @staticmethod
    def run_reconciliation(taxpayer_mst: str) -> dict:
        """Compares customs declarations against import VAT invoices in the system.

        Performs:
          - Exchange rate variance audit against standard accounting rate and invoice notes.
          - HS code risk category checks based on standard Customs audit warnings.
          - Duty rate checks for potential under-reporting or abnormal tax rates.
        """
        import re
        from invoices.tax_mapping import CurrencyExchangeBuffer

        declarations = CustomsDeclaration.query.filter_by(taxpayer_mst=taxpayer_mst).all()
        invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst, invoice_type="purchase").all()
        exchange_buffer = CurrencyExchangeBuffer()

        HIGH_RISK_HS_PREFIXES = {
            "8471": "Thiết bị xử lý dữ liệu tự động (máy vi tính) - Rủi ro khai sai trị giá/áp sai thuế suất.",
            "8517": "Điện thoại và thiết bị truyền phát thông tin - Rủi ro gian lận xuất xứ/thương hiệu.",
            "72": "Sắt, thép và sản phẩm từ sắt, thép - Có nguy cơ áp thuế phòng vệ thương mại / thuế chống bán phá giá.",
            "73": "Sản phẩm bằng sắt hoặc thép - Có nguy cơ áp thuế phòng vệ thương mại.",
            "22": "Đồ uống, rượu và giấm - Thuộc đối tượng chịu Thuế Tiêu thụ Đặc biệt (SCT) và thuế suất cao.",
            "24": "Thuốc lá và nguyên liệu thay thế thuốc lá - Thuộc đối tượng chịu Thuế Tiêu thụ Đặc biệt và kiểm soát nhập khẩu nghiêm ngặt.",
            "87": "Xe cộ trừ phương tiện chạy trên đường sắt - Thuế suất cao, rủi ro khai sai trị giá hải quan.",
            "3808": "Thuốc trừ dịch hại, chất khử trùng - Rủi ro về kiểm tra chuyên ngành và giấy phép môi trường.",
        }

        def extract_exchange_rate_from_text(text: str) -> float | None:
            if not text:
                return None
            patterns = [
                r"(?:tỷ giá|ty gia|rate|exchange\s*rate)[:\s]+([\d.,]+)",
                r"tỷ\s*giá[:\s]+([\d.,]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text.lower())
                if match:
                    raw_val = match.group(1).strip("., ")
                    # Standard parsing of commas/dots for Vietnamese & standard formats
                    if "," in raw_val and "." in raw_val:
                        if raw_val.find(",") < raw_val.find("."):
                            raw_val = raw_val.replace(",", "")
                        else:
                            raw_val = raw_val.replace(".", "").replace(",", ".")
                    elif "," in raw_val:
                        if len(raw_val) - raw_val.rfind(",") == 4:
                            raw_val = raw_val.replace(",", "")
                        else:
                            raw_val = raw_val.replace(",", ".")
                    elif "." in raw_val:
                        if len(raw_val) - raw_val.rfind(".") == 4:
                            raw_val = raw_val.replace(".", "")
                    try:
                        rate = float(raw_val)
                        if 100.0 < rate < 100000.0:
                            return rate
                    except ValueError:
                        continue
            return None

        results = {
            "processed": len(declarations),
            "matched": 0,
            "discrepancies": 0,
            "unresolved": 0
        }

        for decl in declarations:
            # 1. HS code risk audit
            hs_warnings = []
            for hs in decl.hs_codes:
                for prefix, desc in HIGH_RISK_HS_PREFIXES.items():
                    if hs.startswith(prefix):
                        hs_warnings.append(f"Mã HS {hs}: {desc}")

            # 2. Exchange rate variance vs standard buffer rate
            rate_warnings = []
            if decl.currency and decl.currency.upper() != "VND":
                buffer_rate = exchange_buffer.get_rate(decl.currency)
                if buffer_rate and buffer_rate != 1.0:
                    deviation = abs(decl.exchange_rate - buffer_rate) / buffer_rate
                    if deviation > 0.02:
                        rate_warnings.append(
                            f"Tỷ giá tờ khai ({decl.exchange_rate:,.2f}) lệch > 2% so với tỷ giá kế toán chuẩn ({buffer_rate:,.2f}, lệch {deviation * 100:.2f}%)."
                        )

            # 3. Duty rate check
            duty_warnings = []
            if decl.customs_value_vnd > 0:
                implied_duty_rate = decl.import_duty_vnd / decl.customs_value_vnd
                if implied_duty_rate > 0.50:
                    duty_warnings.append(
                        f"Thuế suất nhập khẩu ngầm định rất cao ({implied_duty_rate * 100:.1f}%), cần kiểm tra lại cơ sở tính thuế."
                    )
                elif implied_duty_rate == 0.0:
                    has_high_duty_hs = any(
                        any(hs.startswith(prefix) for prefix in ["72", "73", "22", "24", "87"])
                        for hs in decl.hs_codes
                    )
                    if has_high_duty_hs:
                        duty_warnings.append(
                            "Nhóm HS có thuế suất cao nhưng thuế nhập khẩu khai báo bằng 0. Cảnh báo rủi ro ấn định thuế."
                        )

            # Look for a matching purchase invoice
            matched_inv = None

            # First priority: reference code match
            for inv in invoices:
                desc_text = f"{inv.number} {inv.notes or ''} {inv.filename or ''}".lower()
                if decl.declaration_number.lower() in desc_text:
                    matched_inv = inv
                    break

            # Second priority: exact VAT tax amount match
            if not matched_inv:
                for inv in invoices:
                    if abs(inv.tax_amount - decl.import_vat_vnd) < 1.0:
                        matched_inv = inv
                        break

            all_notes = []

            if matched_inv:
                decl.matching_invoice_id = matched_inv.id
                variance = abs(matched_inv.tax_amount - decl.import_vat_vnd)

                if variance < 10.0:
                    decl.status = "matched"
                    all_notes.append(f"Khớp thuế GTGT hoàn toàn với hóa đơn số {matched_inv.number}.")
                    results["matched"] += 1
                else:
                    decl.status = "variance_exceeded"
                    all_notes.append(
                        f"Chênh lệch thuế GTGT nhập khẩu: Hải quan = {decl.import_vat_vnd:,.0f} VND, "
                        f"Hóa đơn mua vào = {matched_inv.tax_amount:,.0f} VND. "
                        f"Lệch = {matched_inv.tax_amount - decl.import_vat_vnd:,.0f} VND."
                    )
                    results["discrepancies"] += 1

                # Audit exchange rate vs matched invoice
                invoice_rate = extract_exchange_rate_from_text(matched_inv.notes or "")
                if invoice_rate:
                    inv_deviation = abs(decl.exchange_rate - invoice_rate) / invoice_rate
                    if inv_deviation > 0.01:
                        rate_warnings.append(
                            f"Tỷ giá tờ khai ({decl.exchange_rate:,.2f}) lệch > 1% so với tỷ giá thực tế trên hóa đơn ({invoice_rate:,.2f}, lệch {inv_deviation * 100:.2f}%)."
                        )
            else:
                decl.status = "unreconciled"
                all_notes.append("Không tìm thấy hóa đơn thuế GTGT mua vào đối ứng.")
                results["unresolved"] += 1

            # Append warning flags to notes
            if rate_warnings:
                all_notes.append("⚠️ Cảnh báo tỷ giá: " + " | ".join(rate_warnings))
            if hs_warnings:
                all_notes.append("⚠️ Cảnh báo mã HS: " + " | ".join(hs_warnings))
            if duty_warnings:
                all_notes.append("⚠️ Cảnh báo thuế suất: " + " | ".join(duty_warnings))

            decl.variance_notes = " \n".join(all_notes)

        db.session.commit()
        return results
