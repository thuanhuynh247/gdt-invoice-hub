"""Unit tests for Customs VAT Reconciler & XML Parser (US-334, US-335)."""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import CustomsDeclaration, Invoice
from invoices.customs_service import parse_customs_xml, CustomsReconciliationEngine

TEST_CUSTOMS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Declaration>
    <DeclarationNo>CD1002394</DeclarationNo>
    <DeclarationDate>2026-06-03</DeclarationDate>
    <ImporterMST>0101234567</ImporterMST>
    <CustomsValueVND>500000000.0</CustomsValueVND>
    <ImportDutyVND>50000000.0</ImportDutyVND>
    <ImportVATVND>55000000.0</ImportVATVND>
    <CurrencyCode>USD</CurrencyCode>
    <ExchangeRate>25000.0</ExchangeRate>
    <HSCode>84713010</HSCode>
    <HSCode>85171300</HSCode>
</Declaration>
"""


def test_customs_xml_parsing():
    """Test extracting structured data from Customs VNACCS/VCIS declaration XML."""
    data = parse_customs_xml(TEST_CUSTOMS_XML.encode("utf-8"))
    assert data["declaration_number"] == "CD1002394"
    assert data["declaration_date"] == "2026-06-03"
    assert data["taxpayer_mst"] == "0101234567"
    assert data["customs_value_vnd"] == 500000000.0
    assert data["import_duty_vnd"] == 50000000.0
    assert data["import_vat_vnd"] == 55000000.0
    assert data["currency"] == "USD"
    assert data["exchange_rate"] == 25000.0
    assert len(data["hs_codes"]) == 2
    assert "84713010" in data["hs_codes"]


def test_customs_reconciliation_exact_and_discrepancy(app):
    """Test importing declarations and matching with domestic input VAT invoices."""
    with app.app_context():
        # Clear records
        CustomsDeclaration.query.delete()
        Invoice.query.delete()
        db.session.commit()

        # Ingest declaration
        decl = CustomsReconciliationEngine.ingest_declaration(TEST_CUSTOMS_XML.encode("utf-8"))
        assert decl.declaration_number == "CD1002394"
        assert decl.status == "unreconciled"

        # 1. Run reconciliation with no matching invoice
        res1 = CustomsReconciliationEngine.run_reconciliation("0101234567")
        assert res1["unresolved"] == 1
        assert res1["matched"] == 0

        # 2. Add an invoice with matching tax amount (55,000,000 VND)
        inv = Invoice(
            id="inv-import-vat", taxpayer_mst="0101234567", seller_mst="CUSTOMS_VN",
            buyer_mst="0101234567", number="VAT-1002", total_amount=605000000.0,
            amount_before_tax=550000000.0, tax_amount=55000000.0, date="2026-06-03",
            imported_at="2026-06-03T12:00:00Z", invoice_type="purchase",
            notes="CD1002394 import payment"
        )
        db.session.add(inv)
        db.session.commit()

        # Re-run reconciliation
        res2 = CustomsReconciliationEngine.run_reconciliation("0101234567")
        assert res2["matched"] == 1
        assert res2["unresolved"] == 0
        assert decl.status == "matched"
        assert decl.matching_invoice_id == "inv-import-vat"

        # 3. Modify invoice tax amount to simulate discrepancy (e.g. 54,000,000 VND)
        inv.tax_amount = 54000000.0
        db.session.commit()

        res3 = CustomsReconciliationEngine.run_reconciliation("0101234567")
        assert res3["discrepancies"] == 1
        assert decl.status == "variance_exceeded"
        assert "Chênh lệch thuế GTGT nhập khẩu" in decl.variance_notes
