"""Test suite for V17 features: BCTC statutory accounts compilation,

ledger integrity audit, tax payment slip & VietQR, bank cash compliance,
and e-commerce sync & reconciliation.
"""

from __future__ import annotations

import json
from io import BytesIO
import pytest
from extensions import db
from invoices.models import Invoice, LineItem, BankTransaction
from invoices.bctc_service import compile_bctc, audit_ledger_against_invoices
from invoices.tax_payment_service import generate_tax_payment_slip, crc16_ccitt, generate_vietqr_string
from invoices.ecommerce_service import sync_ecommerce_orders, reconcile_ecommerce_tax


def test_crc16_compliance():
    """Verify EMVCo CRC16 compliance function works as specified."""
    # Test vector for CRC-16 CCITT
    data = "123456789"
    # The standard CRC-16/CCITT-FALSE value for "123456789" is 29B1
    assert crc16_ccitt(data) == "29B1"


def test_bctc_compilation_success():
    """Test successful compilation of BCTC statements when equations balance."""
    balances = {
        "111": {"opening_debit": 1000, "opening_credit": 0, "debit_movement": 200, "credit_movement": 100, "closing_debit": 1100, "closing_credit": 0},
        "112": {"opening_debit": 2000, "opening_credit": 0, "debit_movement": 400, "credit_movement": 200, "closing_debit": 2200, "closing_credit": 0},
        "131": {"opening_debit": 500, "opening_credit": 0, "debit_movement": 50, "credit_movement": 50, "closing_debit": 500, "closing_credit": 0},
        "331": {"opening_debit": 0, "opening_credit": 800, "debit_movement": 100, "credit_movement": 300, "closing_debit": 0, "closing_credit": 1000},
        "3331": {"opening_debit": 0, "opening_credit": 200, "debit_movement": 50, "credit_movement": 150, "closing_debit": 0, "closing_credit": 300},
        "411": {"opening_debit": 0, "opening_credit": 2000, "debit_movement": 0, "credit_movement": 0, "closing_debit": 0, "closing_credit": 2000},
        "421": {"opening_debit": 0, "opening_credit": 500, "debit_movement": 0, "credit_movement": 0, "closing_debit": 0, "closing_credit": 500},
        # Income statement accounts
        "511": {"opening_debit": 0, "opening_credit": 0, "debit_movement": 0, "credit_movement": 1000, "closing_debit": 0, "closing_credit": 0},
        "632": {"opening_debit": 0, "opening_credit": 0, "debit_movement": 600, "credit_movement": 0, "closing_debit": 0, "closing_credit": 0},
        "642": {"opening_debit": 0, "opening_credit": 0, "debit_movement": 400, "credit_movement": 0, "closing_debit": 0, "closing_credit": 0},
    }
    
    metadata = {
        "mst": "0109998887",
        "company_name": "CONG TY TNHH MOCK",
        "year": 2026,
        "reporting_period_type": "N",
        "dividends_paid": 0.0
    }
    
    xml_str, warnings = compile_bctc(balances, metadata)
    
    assert len(warnings) == 0
    assert "<HSoKhaiThue>" in xml_str
    assert "<MaMST>0109998887</MaMST>" in xml_str
    assert "<TongCongTaiSan MaSo=\"270\">3800</TongCongTaiSan>" in xml_str
    assert "<TongCongNguonVon MaSo=\"440\">3800</TongCongNguonVon>" in xml_str


def test_bctc_compilation_warnings():
    """Test compilation warnings when Balance Sheet equations do not balance."""
    balances = {
        "111": {"opening_debit": 1000, "opening_credit": 0, "debit_movement": 0, "credit_movement": 0, "closing_debit": 1000, "closing_credit": 0},
        # Total Assets = 1000
        # Let's make Equity/Liabilities = 1200 (out of balance)
        "411": {"opening_debit": 0, "opening_credit": 1200, "debit_movement": 0, "credit_movement": 0, "closing_debit": 0, "closing_credit": 1200},
    }
    
    metadata = {
        "mst": "0109998887",
        "company_name": "CONG TY TNHH MOCK",
        "year": 2026,
        "reporting_period_type": "N",
        "dividends_paid": 0.0
    }
    
    xml_str, warnings = compile_bctc(balances, metadata)
    assert len(warnings) > 0
    assert any("mất cân đối" in w.lower() or "mat can doi" in w.lower() for w in warnings)


def test_tax_payment_slip_generation():
    """Test tax payment slip and VietQR code generation."""
    slip = generate_tax_payment_slip(
        mst="0109998887",
        company_name="CONG TY TNHH MOCK",
        tax_type="vat",
        amount=15000000.0,
        chapter_type="domestic_private",
        treasury_name="Kho bac Cầu Giấy",
        treasury_account="111222333444",
        bank_bin="970415"
    )
    
    assert slip["chapter_code"] == "552"
    assert slip["sub_chapter_code"] == "1701"
    assert slip["vietqr_string"].startswith("000201")
    # Verify presence of state payment specifications in the VietQR string
    assert "970415" in slip["vietqr_string"]
    assert "111222333444" in slip["vietqr_string"]
    assert "15000000" in slip["vietqr_string"]
    assert slip["vietqr_base64"] is not None


def test_ledger_integrity_auditor(app):
    """Test auditing ledger entries against e-invoices."""
    with app.app_context():
        # Clear existing invoices
        Invoice.query.delete()
        db.session.commit()
        
        # Create mock invoices in database
        inv1 = Invoice(
            id="INV-001",
            filename="inv001.xml",
            invoice_type="purchase",
            number="0000001",
            date="2026-05-01",
            currency="VND",
            seller_name="Platform Shopee",
            seller_mst="0109999999",
            buyer_name="Doanh nghiệp của tôi",
            buyer_mst="0109998887",
            amount_before_tax=1000000.0,
            tax_amount=100000.0,
            total_amount=1100000.0,
            payment_method="CK",
            imported_at="2026-05-02",
            taxpayer_mst="0109998887"
        )
        
        # Invoice that won't have a ledger entry (missing entry)
        inv2 = Invoice(
            id="INV-002",
            filename="inv002.xml",
            invoice_type="sale",
            number="0000002",
            date="2026-05-02",
            currency="VND",
            seller_name="Doanh nghiệp của tôi",
            seller_mst="0109998887",
            buyer_name="Client A",
            buyer_mst="1234567890",
            amount_before_tax=5000000.0,
            tax_amount=500000.0,
            total_amount=5500000.0,
            payment_method="CK",
            imported_at="2026-05-03",
            taxpayer_mst="0109998887"
        )
        
        db.session.add(inv1)
        db.session.add(inv2)
        db.session.commit()
        
        # Prepare ledger balances
        balances = {
            # Matches inv1 total amount (1,100,000)
            "331": {"opening_debit": 0, "opening_credit": 0, "debit_movement": 0, "credit_movement": 1100000, "closing_debit": 0, "closing_credit": 1100000},
            # Ledger entry with no matching invoice (missing invoice)
            "642": {"opening_debit": 0, "opening_credit": 0, "debit_movement": 2200000, "credit_movement": 0, "closing_debit": 2200000, "closing_credit": 0},
        }
        
        report = audit_ledger_against_invoices(balances, taxpayer_mst="0109998887")
        
        assert report["status"] == "flagged"
        assert len(report["missing_entries"]) > 0  # inv2 is missing
        assert len(report["missing_invoices"]) > 0  # 2,200,000 ledger entry has no matching invoice


def test_bank_recon_cash_compliance(app):
    """Test cash payment compliance warning on high value invoices."""
    with app.app_context():
        Invoice.query.delete()
        BankTransaction.query.delete()
        db.session.commit()
        
        # High value invoice >= 20M VND paid in Cash
        inv1 = Invoice(
            id="INV-HIGH-CASH",
            filename="inv_high_cash.xml",
            invoice_type="purchase",
            number="0001001",
            date="2026-05-10",
            currency="VND",
            seller_name="Supplier Large",
            seller_mst="0203040506",
            buyer_name="Doanh nghiệp của tôi",
            buyer_mst="0109998887",
            amount_before_tax=25000000.0,
            tax_amount=2500000.0,
            total_amount=27500000.0,
            payment_method="Tien mat", # Violates law
            imported_at="2026-05-11",
            taxpayer_mst="0109998887"
        )
        
        # High value invoice >= 20M VND with bank payment specified but no bank transaction matched
        inv2 = Invoice(
            id="INV-HIGH-CK-UNMATCHED",
            filename="inv_high_ck.xml",
            invoice_type="purchase",
            number="0001002",
            date="2026-05-12",
            currency="VND",
            seller_name="Supplier Large 2",
            seller_mst="0203040507",
            buyer_name="Doanh nghiệp của tôi",
            buyer_mst="0109998887",
            amount_before_tax=30000000.0,
            tax_amount=3000000.0,
            total_amount=33000000.0,
            payment_method="Chuyen khoan",
            imported_at="2026-05-13",
            taxpayer_mst="0109998887"
        )
        
        db.session.add(inv1)
        db.session.add(inv2)
        db.session.commit()
        
        from invoices.bank_reconcile_service import check_cash_payment_compliance
        warnings = check_cash_payment_compliance("0109998887")
        
        # Assertions
        assert len(warnings) == 2
        non_compliant = [w for w in warnings if w["compliance_status"] == "non_compliant"]
        pending = [w for w in warnings if w["compliance_status"] == "pending_verification"]
        
        assert len(non_compliant) == 1
        assert non_compliant[0]["invoice_id"] == "INV-HIGH-CASH"
        assert len(pending) == 1
        assert pending[0]["invoice_id"] == "INV-HIGH-CK-UNMATCHED"


def test_ecommerce_sync_and_reconcile(app):
    """Test e-commerce order ingestion, daily aggregation, and tax matching."""
    with app.app_context():
        Invoice.query.delete()
        LineItem.query.delete()
        db.session.commit()
        
        orders = [
            {
                "order_id": "ORD-SHP-9901",
                "date": "2026-05-20",
                "gross_revenue": 1000000.0,
                "seller_voucher": 50000.0,
                "platform_voucher": 30000.0,
                "commission_fee": 30000.0,
                "service_fee": 10000.0
            },
            {
                "order_id": "ORD-SHP-9902",
                "date": "2026-05-20",
                "gross_revenue": 2000000.0,
                "seller_voucher": 100000.0,
                "platform_voucher": 0.0,
                "commission_fee": 60000.0,
                "service_fee": 20000.0
            }
        ]
        
        # Sync orders
        res = sync_ecommerce_orders(orders, taxpayer_mst="0109998887", platform="Shopee")
        
        assert res["status"] == "success"
        assert res["invoices_created"] == 2 # 1 sales invoice, 1 fee invoice
        
        # Check generated daily sales invoice
        sale_inv = Invoice.query.filter_by(invoice_type="sale").first()
        assert sale_inv is not None
        # Net revenue = (1000000 - 50000) + (2000000 - 100000) = 2850000
        assert sale_inv.amount_before_tax == 2850000.0
        
        # Check generated daily fee invoice
        fee_inv = Invoice.query.filter_by(invoice_type="purchase").first()
        assert fee_inv is not None
        # Total fees = 30000 + 10000 + 60000 + 20000 = 120000
        assert fee_inv.amount_before_tax == 120000.0
        
        # Reconcile orders
        # If we check the synced orders, since we created consolidated invoices
        # containing "ORD-SHP-9901" and "ORD-SHP-9902" in the notes, they should match!
        report = reconcile_ecommerce_tax("0109998887", orders)
        assert report["discrepancy_rate_percent"] == 0.0
        assert report["audit_risk_score"] == 10
        assert len(report["un_invoiced_revenue"]) == 0
        assert len(report["vat_deduction_risk"]) == 0


def test_api_bctc_routes(client):
    """Test API endpoint integration for BCTC compiler and trial balance auditor."""
    # Login client first
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = "0109998887"
        
    balances = {
        "111": {"opening_debit": 100, "opening_credit": 0, "debit_movement": 0, "credit_movement": 0, "closing_debit": 100, "closing_credit": 0},
        "411": {"opening_debit": 0, "opening_credit": 100, "debit_movement": 0, "credit_movement": 0, "closing_debit": 0, "closing_credit": 100},
    }
    
    # 1. Compile endpoint
    resp = client.post("/api/bctc/compile", json={
        "balances": balances,
        "mst": "0109998887",
        "company_name": "CONG TY TNHH MOCK",
        "year": 2026
    })
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "<GiayNopTien>" not in data["xml"] # Should be BCTC tags
    assert "BangCanDoiKeToan" in data["xml"]
    
    # 2. Audit ledger endpoint
    resp = client.post("/api/bctc/audit-ledger", json={
        "balances": balances,
        "taxpayer_mst": "0109998887"
    })
    assert resp.status_code == 200
    assert "compliance_score" in resp.get_json()


def test_api_tax_slip_and_recon_routes(client):
    """Test API endpoints for payments and ecommerce synchronization."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = "0109998887"
        
    # 1. Tax payment slip route
    resp = client.post("/api/payments/tax-slip", json={
        "tax_type": "cit",
        "amount": 25000000.0,
        "chapter_type": "domestic_private"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "xml" in data
    assert "vietqr_string" in data
    assert "vietqr_base64" in data
    
    # 2. E-Commerce sync route
    orders = [
        {"order_id": "ORD-SHOPEE-2001", "date": "2026-05-25", "gross_revenue": 100000.0, "commission_fee": 3000.0, "service_fee": 1000.0}
    ]
    resp = client.post("/api/ecommerce/sync", json={
        "orders": orders,
        "platform": "Shopee",
        "taxpayer_mst": "0109998887"
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    
    # 3. E-Commerce reconcile route
    resp = client.get("/api/ecommerce/reconcile", query_string={
        "orders": json.dumps(orders),
        "taxpayer_mst": "0109998887"
    })
    assert resp.status_code == 200
    assert "audit_risk_score" in resp.get_json()
