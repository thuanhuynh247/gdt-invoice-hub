"""Test suite for V22 features: tax penalty calculator, explanation builder,
e-commerce order normalizer, e-commerce matching engine, payroll auditor, 
and Form 05/QTT-TNCN XML builder.
"""

from __future__ import annotations

import json
import pytest
from extensions import db
from invoices.models import Invoice, LineItem
from invoices.tax_audit_service import calculate_audit_penalties, generate_audit_defense_letter
from invoices.ecommerce_service import normalize_ecommerce_orders, reconcile_ecommerce_tax
from invoices.payroll_pit_service import calculate_monthly_pit, audit_payroll_register, generate_form_05_qtt_tncn_xml


def test_calculate_audit_penalties():
    """Verify statutory tax penalty and daily late payment interest calculation."""
    # Underpayment: 100M VND, 30 days late, no evasion
    res = calculate_audit_penalties(
        underpaid_tax=100000000.0,
        due_date="2026-05-01",
        payment_date="2026-05-31",
        evasion_multiplier=0.0
    )
    
    assert res["late_days"] == 30
    # Fine: 20% of 100M = 20M
    assert res["under_declaration_fine"] == 20000000.0
    # Interest: 100M * 0.0003 * 30 = 900k
    assert res["late_interest"] == 900000.0
    assert res["evasion_fine"] == 0.0
    assert res["total_penalties"] == 20900000.0
    assert res["total_liability"] == 120900000.0

    # With mitigating factors (20% reduction in fines)
    res_mitigated = calculate_audit_penalties(
        underpaid_tax=100000000.0,
        due_date="2026-05-01",
        payment_date="2026-05-31",
        evasion_multiplier=0.0,
        has_mitigating_factors=True
    )
    assert res_mitigated["under_declaration_fine"] == 16000000.0  # 20M * 0.8
    assert res_mitigated["late_interest"] == 900000.0  # Interest is not reduced
    assert res_mitigated["total_penalties"] == 16900000.0


def test_generate_audit_defense_letter():
    """Verify generation of corporate defense letter templates."""
    letter = generate_audit_defense_letter(
        risk_type="RELATED_PARTY_EBITDA",
        taxpayer_name="CONG TY TNHH MOCK",
        taxpayer_mst="0109998887",
        details={
            "actual_interest": 5000000000.0,
            "allowable_interest": 3000000000.0,
            "variance": 2000000000.0
        }
    )
    assert "Nghị định 132/2020/NĐ-CP" in letter
    assert "CONG TY TNHH MOCK" in letter
    assert "5,000,000,000" in letter
    assert "2,000,000,000" in letter


def test_normalize_ecommerce_orders():
    """Verify normalization of Shopee, Lazada and TikTok Shop order structures."""
    # Shopee raw format
    shopee_raw = [{
        "Order ID": "SHP-12345",
        "Completed Date": "2026-05-15 14:30:00",
        "Gross Sales": "1500000",
        "Seller Voucher": "50000",
        "Shopee Voucher": "10000",
        "Fixed Fee": "45000",
        "Service Fee": "15000"
    }]
    shopee_norm = normalize_ecommerce_orders(shopee_raw, "Shopee")
    assert shopee_norm[0]["order_id"] == "SHP-12345"
    assert shopee_norm[0]["date"] == "2026-05-15"
    assert shopee_norm[0]["gross_revenue"] == 1500000.0
    assert shopee_norm[0]["seller_voucher"] == 50000.0
    assert shopee_norm[0]["commission_fee"] == 45000.0
    
    # Lazada raw format
    lazada_raw = [{
        "Order Number": "LAZ-999",
        "Transaction Date": "2026-05-16",
        "Amount": "2000000",
        "Lazada Voucher": "20000",
        "Seller Voucher": "100000",
        "Commission": "60000",
        "Payment Fee": "20000"
    }]
    lazada_norm = normalize_ecommerce_orders(lazada_raw, "Lazada")
    assert lazada_norm[0]["order_id"] == "LAZ-999"
    assert lazada_norm[0]["gross_revenue"] == 2000000.0
    assert lazada_norm[0]["platform_voucher"] == 20000.0
    assert lazada_norm[0]["service_fee"] == 20000.0

    # TikTok Shop raw format
    tiktok_raw = [{
        "Order ID": "TT-777",
        "Settlement Time": "2026-05-17",
        "Gross Revenue": "800000",
        "Seller Coupon": "30000",
        "TikTok Shop Coupon": "10000",
        "Platform Fee": "24000",
        "Subsidized Shipping Fee": "8000"
    }]
    tiktok_norm = normalize_ecommerce_orders(tiktok_raw, "TikTok Shop")
    assert tiktok_norm[0]["order_id"] == "TT-777"
    assert tiktok_norm[0]["gross_revenue"] == 800000.0
    assert tiktok_norm[0]["seller_voucher"] == 30000.0
    assert tiktok_norm[0]["commission_fee"] == 24000.0


def test_ecommerce_matching_and_warnings(app):
    """Verify invoice matching engine raises compliance warning tags and price mismatches."""
    with app.app_context():
        # Clear database invoices and line items
        Invoice.query.delete()
        LineItem.query.delete()
        db.session.commit()
        
        # 1. Seed a sales invoice referencing ORD-001 but with price mismatch
        # Expected net: 1,000,000 - 50,000 = 950,000.
        # But we record 800,000 in line item (price mismatch)
        sale_inv = Invoice(
            id="INV-RECON-1",
            filename="inv_recon_1.xml",
            invoice_type="sale",
            number="0001234",
            date="2026-05-20",
            currency="VND",
            seller_name="Doanh nghiệp của tôi",
            seller_mst="0109998887",
            buyer_name="Client A",
            buyer_mst="1234567890",
            amount_before_tax=800000.0,
            tax_amount=80000.0,
            total_amount=880000.0,
            payment_method="TMĐT",
            imported_at="2026-05-21",
            notes="Consolidated daily retail sales. Orders: ORD-001",
            taxpayer_mst="0109998887"
        )
        item = LineItem(
            invoice_id="INV-RECON-1",
            item_name="Bán lẻ qua sàn Shopee đơn ORD-001",
            quantity=1.0,
            unit_price=800000.0,
            amount_before_tax=800000.0,
            tax_rate="10%",
            tax_amount=80000.0
        )
        db.session.add(sale_inv)
        db.session.add(item)
        db.session.commit()
        
        # Platform orders list
        orders = [
            # Matches ORD-001 (but price mismatched: gross=1000000, seller_v=50000 -> net=950000 vs 800000)
            {
                "order_id": "ORD-001",
                "date": "2026-05-20",
                "gross_revenue": 1000000.0,
                "seller_voucher": 50000.0,
                "platform_voucher": 0.0,
                "commission_fee": 30000.0,
                "service_fee": 10000.0
            },
            # ORD-002: Uninvoiced (missing invoice)
            {
                "order_id": "ORD-002",
                "date": "2026-05-20",
                "gross_revenue": 500000.0,
                "seller_voucher": 0.0,
                "platform_voucher": 0.0,
                "commission_fee": 15000.0,
                "service_fee": 5000.0
            }
        ]
        
        report = reconcile_ecommerce_tax("0109998887", orders)
        
        # Verify warnings and types
        assert len(report["un_invoiced_revenue"]) == 1
        assert report["un_invoiced_revenue"][0]["order_id"] == "ORD-002"
        assert report["un_invoiced_revenue"][0]["warning_type"] == "UNINVOICED_SALES_WARNING"
        
        assert len(report["price_mismatches"]) == 1
        assert report["price_mismatches"][0]["order_id"] == "ORD-001"
        assert report["price_mismatches"][0]["warning_type"] == "PRICE_MISMATCH_WARNING"
        assert report["price_mismatches"][0]["order_amount"] == 950000.0
        assert report["price_mismatches"][0]["invoice_amount"] == 800000.0
        
        # Check warnings code lists
        codes = [w["code"] for w in report["warnings"]]
        assert "UNINVOICED_SALES_WARNING" in codes
        assert "PRICE_MISMATCH_WARNING" in codes


def test_payroll_pit_progressive_calculations():
    """Verify progressive PIT tax brackets calculation logic."""
    # Under 5M taxable: 5%
    assert calculate_monthly_pit(4000000.0) == 200000.0
    
    # 8M taxable: 10% - 250k = 550k
    assert calculate_monthly_pit(8000000.0) == 550000.0
    
    # 15M taxable: 15% - 750k = 1.5M
    assert calculate_monthly_pit(15000000.0) == 1500000.0
    
    # 25M taxable: 20% - 1.65M = 3.35M
    assert calculate_monthly_pit(25000000.0) == 3350000.0


def test_payroll_register_auditor():
    """Verify payroll social insurance and PIT withholding audits."""
    employees = [
        # Compliant employee: gross=30M, dependents=1. Deductions = 11M + 4.4M + 3.15M (SI) = 18.55M.
        # Taxable = 11.45M. PIT = 11.45M * 0.15 - 750k = 967,500.
        {
            "id": "EMP-001",
            "name": "Nguyen Van A",
            "mst": "8012345678",
            "gross_salary": 30000000.0,
            "dependents": 1,
            "withheld_pit": 967500.0,
            "withheld_insurance": 3150000.0
        },
        # Non-compliant employee (discrepancies in both PIT and insurance)
        {
            "id": "EMP-002",
            "name": "Tran Thi B",
            "mst": "8012345679",
            "gross_salary": 20000000.0,
            "dependents": 0,
            "withheld_pit": 500000.0,  # Wrong PIT
            "withheld_insurance": 1500000.0  # Wrong insurance (should be 2.1M)
        }
    ]
    
    report = audit_payroll_register(employees)
    
    assert report["compliance_score"] == 50  # 2 warnings raised on EMP-002
    assert report["status"] == "flagged"
    assert len(report["compliance_issues"]) == 2
    
    issues = [iss["issue_type"] for iss in report["compliance_issues"]]
    assert "PIT_DISCREPANCY" in issues
    assert "SI_DISCREPANCY" in issues


def test_form_05_qtt_tncn_xml_generation():
    """Verify generation of compliant Form 05/QTT-TNCN XML return."""
    metadata = {
        "mst": "0109998887",
        "company_name": "CONG TY TNHH MOCK",
        "year": 2026
    }
    employees = [
        {
            "name": "Nguyen Van A",
            "mst": "8012345678",
            "contract_type": "long_term",
            "gross_salary": 30000000.0,
            "dependents": 1,
            "withheld_insurance": 3150000.0
        },
        {
            "name": "Tran Thi B",
            "mst": "8012345679",
            "contract_type": "short_term",
            "gross_salary": 5000000.0,
            "dependents": 0,
            "withheld_insurance": 0.0
        }
    ]
    
    xml_str = generate_form_05_qtt_tncn_xml(metadata, employees)
    
    assert "<MaMST>0109998887</MaMST>" in xml_str
    assert "<MauTK>05/QTT-TNCN</MauTK>" in xml_str
    assert "<BangKe05_1>" in xml_str
    assert "<BangKe05_2>" in xml_str
    assert "<TenNV>Nguyen Van A</TenNV>" in xml_str
    assert "<TenNV>Tran Thi B</TenNV>" in xml_str


def test_api_v22_endpoints(client):
    """Test flask API integration endpoints for V22 features."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = "0109998887"
        
    # 1. Tax penalties route
    resp = client.post("/api/audit/calculate-penalties", json={
        "underpaid_tax": 50000000.0,
        "due_date": "2026-05-01",
        "payment_date": "2026-06-10",
        "evasion_multiplier": 0.0,
        "has_mitigating_factors": False
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["calculation"]["late_days"] == 40
    assert data["calculation"]["under_declaration_fine"] == 10000000.0
    
    # 2. Defense letter route
    resp = client.post("/api/audit/generate-explanation", json={
        "risk_type": "CIRCULAR_20_RISK",
        "taxpayer_name": "CONG TY TNHH MOCK",
        "details": {
            "invoice_id": "INV-0011",
            "total_amount": 15000000.0
        }
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "Thông tư 20" in data["letter"]
    
    # 3. Normalization route
    resp = client.post("/api/ecommerce/normalize-orders", json={
        "platform": "Lazada",
        "orders": [
            {"Order Number": "LAZ-999", "Transaction Date": "2026-05-16", "Amount": "2000000"}
        ]
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["orders"][0]["order_id"] == "LAZ-999"
    assert data["orders"][0]["gross_revenue"] == 2000000.0
    
    # 4. Payroll audit summary route
    employees = [
        {
            "id": "EMP-100",
            "name": "Employee X",
            "gross_salary": 25000000.0,
            "dependents": 0,
            "withheld_pit": 2500000.0,  # Compliant? No, calculated will be 14.05M taxable -> pit = 14.05M * 0.15 - 750k = 1.3575M
            "withheld_insurance": 2625000.0
        }
    ]
    resp = client.post("/api/payroll/audit-summary", json={
        "employees": employees
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "employees" in data
    assert data["compliance_score"] < 100
    
    # 5. Export PIT XML route
    resp = client.post("/api/payroll/export-pit-xml", json={
        "metadata": {
            "mst": "0109998887",
            "company_name": "CONG TY TNHH MOCK",
            "year": 2026
        },
        "employees": employees
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "<MauTK>05/QTT-TNCN</MauTK>" in data["xml"]
