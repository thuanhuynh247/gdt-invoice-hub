"""Tests for the v4.2.0 VAT Refund Eligibility & AI Dossier Compiler."""

from __future__ import annotations

import json
from datetime import datetime
from extensions import db
from invoices.models import Invoice, LineItem, AIAuditResult, TaxpayerProfile, BankTransaction


def _seed_refund_test_data(app):
    """Seed multi-MST profile and invoice records for testing VAT refunds."""
    with app.app_context():
        # Clear existing
        LineItem.query.delete()
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        BankTransaction.query.delete()
        db.session.commit()

        # 1. Create Taxpayer Profile
        profile = TaxpayerProfile(
            mst="0109998887",
            company_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            gdt_username="toancau_gdt",
            gdt_password_encrypted="encrypted_pass",
            is_active=True,
            created_at=datetime.now().isoformat()
        )
        db.session.add(profile)
        db.session.commit()

        # 2. Seed Sales (to calculate Export Ratio)
        # Sales 1: Standard Domestic Sale (1B VND)
        sale_domestic = Invoice(
            id="SALE-DOM-01",
            filename="sale_dom_1.xml",
            invoice_type="sale",
            number="1001",
            date="2026-05-10",
            currency="VND",
            seller_mst="0109998887",
            seller_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            buyer_mst="0311223344",
            buyer_name="KHACH HANG DOMESTIC",
            amount_before_tax=1000000000.0,
            tax_amount=100000000.0,
            total_amount=1100000000.0,
            has_signature=True,
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )
        # Sales 2: Export Sale (200M VND, 0% VAT)
        sale_export = Invoice(
            id="SALE-EXP-01",
            filename="sale_exp_1.xml",
            invoice_type="sale",
            number="1002",
            date="2026-05-15",
            currency="VND",
            seller_mst="0109998887",
            seller_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            buyer_mst="099888777",
            buyer_name="OVERSEAS BUYER LTD",
            amount_before_tax=200000000.0,
            tax_amount=0.0,
            total_amount=200000000.0,
            has_signature=True,
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )
        db.session.add_all([sale_domestic, sale_export])
        db.session.commit()

        # Add line item with 0% tax rate to qualify as export
        item_export = LineItem(
            invoice_id="SALE-EXP-01",
            item_name="Phan mem xuat khau",
            quantity=1,
            unit_price=200000000.0,
            amount_before_tax=200000000.0,
            tax_rate="0%",
            tax_amount=0.0
        )
        db.session.add(item_export)
        db.session.commit()

        # 3. Seed Purchases (VAT Input)
        # Purchase 1: Valid Input (320M VAT) -> Eligible
        pur_valid = Invoice(
            id="PUR-VAL-01",
            filename="pur_val_1.xml",
            invoice_type="purchase",
            number="2001",
            date="2026-05-12",
            currency="VND",
            seller_mst="0104444333",
            seller_name="NHA CUNG CAP XANG DAU",
            buyer_mst="0109998887",
            buyer_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            amount_before_tax=3200000000.0,
            tax_amount=320000000.0,
            total_amount=3520000000.0,
            has_signature=True,
            t_score=85,
            payment_method="Chuyển khoản ngân hàng",
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )
        
        # Purchase 2: Ineligible due to low T-Score (50M VAT)
        pur_low_t = Invoice(
            id="PUR-LOW-T-01",
            filename="pur_low_t.xml",
            invoice_type="purchase",
            number="2002",
            date="2026-05-14",
            currency="VND",
            seller_mst="010555666",
            seller_name="CONG TY MA",
            buyer_mst="0109998887",
            buyer_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            amount_before_tax=500000000.0,
            tax_amount=50000000.0,
            total_amount=550000000.0,
            has_signature=True,
            t_score=30,
            payment_method="Chuyển khoản",
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )

        # Purchase 3: Ineligible due to cash payment of high value invoice (30M VAT)
        pur_cash = Invoice(
            id="PUR-CASH-01",
            filename="pur_cash.xml",
            invoice_type="purchase",
            number="2003",
            date="2026-05-16",
            currency="VND",
            seller_mst="010777888",
            seller_name="CUA HANG BAN BUON",
            buyer_mst="0109998887",
            buyer_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            amount_before_tax=300000000.0,
            tax_amount=30000000.0,
            total_amount=330000000.0,
            has_signature=True,
            t_score=90,
            payment_method="Tiền mặt",
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )

        db.session.add_all([pur_valid, pur_low_t, pur_cash])
        db.session.commit()

        # Seed matching bank transaction for PUR-VAL-01 to satisfy Rule 5b (non-cash bank payment matching)
        tx_match = BankTransaction(
            id="TX-VAL-01",
            taxpayer_mst="0109998887",
            bank_name="Vietcombank",
            transaction_date="2026-05-13",
            description="THANH TOAN TIEN MUA XANG DAU THEO HD 2001",
            amount=-3520000000.0,
            status="matched",
            matched_invoice_id="PUR-VAL-01",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(tx_match)
        db.session.commit()


def test_vat_refund_eligibility_calculations(app):
    """Verify refund eligibility engine metrics, exclusions, and rates."""
    _seed_refund_test_data(app)

    with app.app_context():
        from invoices.refund_service import VATRefundEligibilityEngine
        engine = VATRefundEligibilityEngine()
        res = engine.get_eligibility("0109998887")

        assert res["is_eligible"] is True
        assert res["status"] in ["Safe", "Caution"]
        
        metrics = res["metrics"]
        # Total domestic sales (1B) + export sales (200M) = 1.2B
        assert metrics["total_sales_amount"] == 1200000000.0
        assert metrics["export_sales_amount"] == 200000000.0
        # Export ratio = 200M / 1.2B = 16.67% >= 10%
        assert round(metrics["export_ratio"], 4) == 0.1667

        # Total input VAT = 320M + 50M + 30M = 400M
        assert metrics["total_input_vat"] == 400000000.0
        # Eligible input VAT = 320M >= 300M threshold
        assert metrics["eligible_input_vat"] == 320000000.0
        # Disqualified input VAT = 50M (low T) + 30M (cash) = 80M
        assert metrics["disqualified_input_vat"] == 80000000.0

        assert len(res["eligible_invoices"]) == 1
        assert len(res["ineligible_invoices"]) == 2


def test_vat_refund_dossier_generation(app):
    """Verify Circular 80 Mẫu 01/HT compiled dossier and AI report fallback text."""
    _seed_refund_test_data(app)

    with app.app_context():
        from invoices.refund_service import VATRefundEligibilityEngine
        engine = VATRefundEligibilityEngine()
        res = engine.generate_dossier("0109998887")

        assert res["status"] == "success"
        assert "MẪU 01/HT" in res["mau_01_ht"]
        assert "GIẤY ĐỀ NGHỊ HOÀN TRẢ KHOẢN THU NGÂN SÁCH NHÀ NƯỚC" in res["mau_01_ht"]
        assert "0109998887" in res["mau_01_ht"]
        
        # Báo cáo phòng vệ AI
        assert "BÁO CÁO PHÂN TÍCH RỦI RO & BẢO VỆ HỒ SƠ" in res["justification_letter"]
        assert "Tiền mặt" in res["justification_letter"] or "tiền mặt" in res["justification_letter"].lower()


def test_api_vat_refund_eligibility_endpoint(logged_in_client, app):
    """Verify GET /api/reports/vat-refund-eligibility endpoint results."""
    _seed_refund_test_data(app)

    response = logged_in_client.get("/api/reports/vat-refund-eligibility?mst=0109998887")
    assert response.status_code == 200
    
    payload = response.get_json()
    assert payload["is_eligible"] is True
    assert payload["metrics"]["eligible_input_vat"] == 320000000.0


def test_api_vat_refund_dossier_endpoint(logged_in_client, app):
    """Verify POST /api/reports/vat-refund-eligibility/dossier endpoint results."""
    _seed_refund_test_data(app)

    response = logged_in_client.post(
        "/api/reports/vat-refund-eligibility/dossier",
        json={"mst": "0109998887"}
    )
    assert response.status_code == 200
    
    payload = response.get_json()
    assert payload["status"] == "success"
    assert "MẪU 01/HT" in payload["mau_01_ht"]


def test_api_export_vat_refund_dossier_endpoint(logged_in_client):
    """Verify POST /api/reports/vat-refund-eligibility/dossier/export formats (Word/PDF)."""
    # 1. Export as Word (.doc)
    response_word = logged_in_client.post(
        "/api/reports/vat-refund-eligibility/dossier/export",
        json={
            "content": "TEST CONTENT WORD",
            "format": "doc",
            "type": "dossier"
        }
    )
    assert response_word.status_code == 200
    assert response_word.mimetype == "application/msword"
    assert b"TEST CONTENT WORD" in response_word.data

    # 2. Export as PDF (.pdf)
    response_pdf = logged_in_client.post(
        "/api/reports/vat-refund-eligibility/dossier/export",
        json={
            "content": "TEST CONTENT PDF",
            "format": "pdf",
            "type": "justification"
        }
    )
    assert response_pdf.status_code == 200
    assert response_pdf.mimetype == "application/pdf"


def test_api_audit_vat_refund_eligibility_with_customs(logged_in_client, app):
    """Verify POST /api/audit/vat-refund-eligibility endpoint works with custom input_invoice_ids and customs_declarations."""
    _seed_refund_test_data(app)

    customs_declarations = [
        {
            "declaration_number": "HQ-2026-001",
            "product_description": "Phan mem xuat khau",
            "quantity": 1,
            "customs_value_vnd": 200000000.0
        },
        {
            "declaration_number": "HQ-2026-002",
            "product_description": "Unmatched Product",
            "quantity": 5,
            "customs_value_vnd": 150000000.0
        }
    ]

    response = logged_in_client.post(
        "/api/audit/vat-refund-eligibility",
        json={
            "mst": "0109998887",
            "input_invoice_ids": ["PUR-VAL-01"],
            "customs_declarations": customs_declarations
        }
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mst"] == "0109998887"
    assert payload["is_eligible"] is True
    
    # Verify customs reconciliation list
    recon = payload["customs_export_reconciliation"]
    assert len(recon) == 2
    
    # First one should be matched
    assert recon[0]["declaration_number"] == "HQ-2026-001"
    assert recon[0]["match_status"] == "Fully Matched"
    assert recon[0]["invoice_number"] == "1002"
    
    # Second one should be unmatched
    assert recon[1]["declaration_number"] == "HQ-2026-002"
    assert recon[1]["match_status"] == "Unmatched"
    assert recon[1]["invoice_number"] is None


def test_api_audit_export_refund_xml_endpoint(logged_in_client, app):
    """Verify POST /api/audit/export-refund-xml endpoint returns valid XML structure."""
    _seed_refund_test_data(app)

    response = logged_in_client.post(
        "/api/audit/export-refund-xml",
        json={
            "mst": "0109998887",
            "eligible_invoice_ids": ["PUR-VAL-01"],
            "bank_account": "123456789",
            "bank_name": "Vietcombank",
            "reason_type": "export"
        }
    )
    assert response.status_code == 200
    assert response.mimetype == "application/xml"
    
    xml_data = response.data.decode("utf-8")
    assert "<MaTKhai>01_DNHT</MaTKhai>" in xml_data
    assert "<Mst>0109998887</Mst>" in xml_data
    assert "<TaiKhoanNhanHoan>123456789</TaiKhoanNhanHoan>" in xml_data
    assert "<TenNganHangNhanHoan>Vietcombank</TenNganHangNhanHoan>" in xml_data
    assert "<VATAmount>320000000.00</VATAmount>" in xml_data

