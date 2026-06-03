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
        """Compares customs declarations against import VAT invoices in the system."""
        declarations = CustomsDeclaration.query.filter_by(taxpayer_mst=taxpayer_mst).all()
        invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst, invoice_type="purchase").all()

        results = {
            "processed": len(declarations),
            "matched": 0,
            "discrepancies": 0,
            "unresolved": 0
        }

        for decl in declarations:
            # Look for a matching purchase invoice
            # Strategy: matches by declaration number in notes/filename/number, or matches by exact tax amount
            matched_inv = None

            # First priority: reference code match
            for inv in invoices:
                # Check if declaration number is mentioned in notes, number, or filename
                desc_text = f"{inv.number} {inv.notes or ''} {inv.filename or ''}".lower()
                if decl.declaration_number.lower() in desc_text:
                    matched_inv = inv
                    break

            # Second priority: exact VAT tax amount match
            if not matched_inv:
                for inv in invoices:
                    # Look for input tax matching declaration import vat
                    if abs(inv.tax_amount - decl.import_vat_vnd) < 1.0:
                        matched_inv = inv
                        break

            if matched_inv:
                decl.matching_invoice_id = matched_inv.id
                # Compare VAT amounts
                variance = abs(matched_inv.tax_amount - decl.import_vat_vnd)
                if variance < 10.0:  # Threshold for rounding differences
                    decl.status = "matched"
                    decl.variance_notes = f"Khớp hoàn toàn với hóa đơn số {matched_inv.number}."
                    results["matched"] += 1
                else:
                    decl.status = "variance_exceeded"
                    decl.variance_notes = (
                        f"Chênh lệch thuế GTGT nhập khẩu: Hải quan = {decl.import_vat_vnd:,.0f} VND, "
                        f"Hóa đơn mua vào = {matched_inv.tax_amount:,.0f} VND. "
                        f"Lệch = {matched_inv.tax_amount - decl.import_vat_vnd:,.0f} VND."
                    )
                    results["discrepancies"] += 1
            else:
                decl.status = "unreconciled"
                decl.variance_notes = "Không tìm thấy hóa đơn thuế GTGT mua vào đối ứng."
                results["unresolved"] += 1

        db.session.commit()
        return results
