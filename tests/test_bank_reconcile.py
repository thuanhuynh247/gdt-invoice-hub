"""Tests for US-080/US-081 AI-Powered Bank Reconciliation."""

from __future__ import annotations

import json
from datetime import datetime
from extensions import db
from invoices.models import Invoice, TaxpayerProfile, BankTransaction
from invoices.bank_reconcile_service import (
    remove_vietnamese_diacritics,
    clean_vietnamese_text,
    clean_company_name_tokens,
    find_matching_invoice
)


def _seed_reconciliation_test_data(app):
    """Seed sample taxpayer profile, sales/purchases invoices and transactions."""
    with app.app_context():
        # Clear existing
        BankTransaction.query.delete()
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
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

        # 2. Seed Sales Invoice (for credit matching)
        inv_sale = Invoice(
            id="SALE-1002",
            filename="sale_1002.xml",
            invoice_type="sale",
            number="1002",
            date="2026-05-15",
            currency="VND",
            seller_mst="0109998887",
            seller_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            buyer_mst="0311223344",
            buyer_name="CONG TY TNHH THUONG MAI AN BINH",
            amount_before_tax=10000000.0,
            tax_amount=1000000.0,
            total_amount=11000000.0,
            has_signature=True,
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )
        
        # 3. Seed Purchase Invoice (for debit matching)
        inv_pur = Invoice(
            id="PUR-2005",
            filename="pur_2005.xml",
            invoice_type="purchase",
            number="2005",
            date="2026-05-20",
            currency="VND",
            seller_mst="0104444333",
            seller_name="CONG TY CO PHAN PHAN PHOI TRUNG NGUYEN",
            buyer_mst="0109998887",
            buyer_name="CONG TY CO PHAN CONG NGHE TOAN CAU",
            amount_before_tax=5000000.0,
            tax_amount=500000.0,
            total_amount=5500000.0,
            has_signature=True,
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )
        db.session.add_all([inv_sale, inv_pur])
        db.session.commit()


def test_vietnamese_text_cleaners():
    """Verify diacritics removal and abbreviation expansion helpers."""
    assert remove_vietnamese_diacritics("Đồng Bằng Sông Cửu Long") == "Dong Bang Song Cuu Long"
    assert clean_vietnamese_text("Công Ty Cổ Phần Công Nghệ Toàn Cầu!!") == "CONG TY CO PHAN CONG NGHE TOAN CAU"
    
    tokens = clean_company_name_tokens("CÔNG TY TNHH PHÂN PHỐI TRUNG NGUYỄN")
    assert "TRUNG" in tokens
    assert "NGUYEN" in tokens
    # Drop words should be removed
    assert "CONG TY" not in tokens
    assert "TNHH" not in tokens


def test_fuzzy_matching_logic(app):
    """Assert phonetic soundex and amount heuristics match correctly."""
    _seed_reconciliation_test_data(app)
    
    with app.app_context():
        # Case 1: Perfect credit match (Sale Invoice)
        tx_credit = BankTransaction(
            id="TX-MOCK-01",
            taxpayer_mst="0109998887",
            bank_name="Vietcombank",
            transaction_date="2026-05-18",
            description="AN BINH CHUYEN TIEN THANH TOAN HD 1002",
            amount=11000000.0,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(tx_credit)
        db.session.commit()
        
        matched_id, score = find_matching_invoice(tx_credit)
        assert matched_id == "SALE-1002"
        assert score >= 0.85
        
        # Case 2: Perfect debit match (Purchase Invoice)
        tx_debit = BankTransaction(
            id="TX-MOCK-02",
            taxpayer_mst="0109998887",
            bank_name="Techcombank",
            transaction_date="2026-05-22",
            description="TRUNG NGUYEN CK HD2005",
            amount=-5500000.0,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(tx_debit)
        db.session.commit()
        
        matched_id, score = find_matching_invoice(tx_debit)
        assert matched_id == "PUR-2005"
        assert score >= 0.85


def test_api_auto_reconciliation_endpoint(logged_in_client, app):
    """Test auto-reconciliation REST API execution and response schemas."""
    _seed_reconciliation_test_data(app)
    
    with app.app_context():
        # Inject matching transactions to run auto matching
        tx1 = BankTransaction(
            id="TX-MOCK-03",
            taxpayer_mst="0109998887",
            bank_name="Vietcombank",
            transaction_date="2026-05-18",
            description="AN BINH CK THANH TOAN HD 1002",
            amount=11000000.0,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        tx2 = BankTransaction(
            id="TX-MOCK-04",
            taxpayer_mst="0109998887",
            bank_name="Techcombank",
            transaction_date="2026-05-22",
            description="MOCK NO MATCHING TRANSACTION DETAILS",
            amount=-9999999.0,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add_all([tx1, tx2])
        db.session.commit()

    # Login and simulate session
    with logged_in_client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["active_taxpayer_mst"] = "0109998887"

    response = logged_in_client.post(
        "/api/bank/reconcile/auto",
        json={"taxpayer_mst": "0109998887"}
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    # Matches found must be 1 (tx1 matches, tx2 fails amount constraint check)
    assert data["matches_found"] == 1
    assert data["details"][0]["transaction_id"] == "TX-MOCK-03"
    assert data["details"][0]["matched_invoice_id"] == "SALE-1002"
    assert "100%" in data["details"][0]["confidence"] or "95%" in data["details"][0]["confidence"] or "90%" in data["details"][0]["confidence"]


def test_api_manual_reconciliation_override(logged_in_client, app):
    """Test manual reconciliation overriding and setting 100% confidence."""
    _seed_reconciliation_test_data(app)
    
    with app.app_context():
        tx = BankTransaction(
            id="TX-MOCK-05",
            taxpayer_mst="0109998887",
            bank_name="Vietcombank",
            transaction_date="2026-05-18",
            description="RANDOM DESCRIPTION NO MATCH AT ALL",
            amount=11000000.0,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(tx)
        db.session.commit()

    with logged_in_client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["active_taxpayer_mst"] = "0109998887"

    response = logged_in_client.post(
        "/api/bank/reconcile/manual",
        json={
            "transaction_id": "TX-MOCK-05",
            "invoice_id": "SALE-1002"
        }
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["details"]["matched_invoice_id"] == "SALE-1002"
    assert data["details"]["invoice_number"] == "1002"

    with app.app_context():
        updated_tx = BankTransaction.query.get("TX-MOCK-05")
        assert updated_tx.status == "matched"
        assert updated_tx.matched_invoice_id == "SALE-1002"
        assert updated_tx.confidence_score == 1.0

