"""Tests for the Vietnamese VAT Declaration Draft & Tax Optimizer endpoint."""

from __future__ import annotations

from datetime import datetime
from extensions import db
from invoices.models import Invoice, LineItem


def _seed_vat_test_invoices(app):
    """Seed test sales (sold) and purchase invoices for VAT return calculations."""
    with app.app_context():
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

        # --- OUTPUTS (Sold) ---
        # 1. Sold Invoice 1: May 2026, 10% VAT
        inv_s1 = Invoice(
            id="SOLD-001",
            filename="sold_1.xml",
            invoice_type="sold",
            number="0001",
            date="2026-05-10",
            currency="VND",
            seller_mst="0109999999",
            seller_name="CONG TY HOC TAP",
            buyer_mst="0201234567",
            buyer_name="KHACH HANG A",
            amount_before_tax=10000000.0,
            tax_amount=1000000.0,
            total_amount=11000000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )
        
        # 2. Sold Invoice 2: May 2026, 5% VAT (with LineItems to test rate classification)
        inv_s2 = Invoice(
            id="SOLD-002",
            filename="sold_2.xml",
            invoice_type="sold",
            number="0002",
            date="2026-05-15",
            currency="VND",
            seller_mst="0109999999",
            seller_name="CONG TY HOC TAP",
            buyer_mst="0209876543",
            buyer_name="KHACH HANG B",
            amount_before_tax=5000000.0,
            tax_amount=250000.0,
            total_amount=5250000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )
        
        item_s2 = LineItem(
            invoice_id="SOLD-002",
            item_name="Dich vu 5% VAT",
            quantity=1,
            unit_price=5000000.0,
            amount_before_tax=5000000.0,
            tax_rate="5%",
            tax_amount=250000.0
        )

        # 3. Sold Invoice 3: April 2026 (same Q2 but different month), 0% VAT
        inv_s3 = Invoice(
            id="SOLD-003",
            filename="sold_3.xml",
            invoice_type="sold",
            number="0003",
            date="2026-04-20",
            currency="VND",
            seller_mst="0109999999",
            seller_name="CONG TY HOC TAP",
            buyer_mst="0301112223",
            buyer_name="KHACH HANG NUOC NGOAI",
            amount_before_tax=20000000.0,
            tax_amount=0.0,
            total_amount=20000000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )

        item_s3 = LineItem(
            invoice_id="SOLD-003",
            item_name="Hang xuat khau 0%",
            quantity=10,
            unit_price=2000000.0,
            amount_before_tax=20000000.0,
            tax_rate="0%",
            tax_amount=0.0
        )

        # --- INPUTS (Purchase) ---
        # 4. Valid Input: May 2026, 10% VAT, No warnings (deductible)
        inv_p1 = Invoice(
            id="PURCHASE-001",
            filename="purchase_1.xml",
            invoice_type="purchase",
            number="0100",
            date="2026-05-12",
            currency="VND",
            seller_mst="0105555555",
            seller_name="NHA CUNG CAP TOT",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=8000000.0,
            tax_amount=800000.0,
            total_amount=8800000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )

        # 5. Invalid Input (Disputed): May 2026, cash warning (not deductible by default)
        inv_p2 = Invoice(
            id="PURCHASE-002",
            filename="purchase_2.xml",
            invoice_type="purchase",
            number="0101",
            date="2026-05-14",
            currency="VND",
            seller_mst="0106666666",
            seller_name="CUA HANG BAN LE",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=6000000.0,
            tax_amount=600000.0,
            total_amount=6600000.0,
            has_signature=True,
            payment_method="Tiền mặt",
            warnings_json='["Hóa đơn thanh toán tiền mặt 5 triệu VND trở lên không được khấu trừ"]',
            imported_at=datetime.now().isoformat()
        )

        db.session.add_all([inv_s1, inv_s2, inv_s3, inv_p1, inv_p2])
        db.session.commit()
        db.session.add_all([item_s2, item_s3])
        db.session.commit()


def test_vat_declaration_requires_login(client):
    """Anonymous users should be blocked with 401."""
    response = client.get("/api/reports/vat-declaration")
    assert response.status_code == 401


def test_vat_declaration_empty(logged_in_client, app):
    """Verify response when database contains no invoices."""
    with app.app_context():
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

    response = logged_in_client.get("/api/reports/vat-declaration?period_type=monthly&period_value=05&year=2026")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["period_value"] == "05"
    assert payload["year"] == "2026"
    assert payload["outputs"]["total_val"] == 0.0
    assert payload["inputs"]["total_value"] == 0.0
    assert len(payload["disputed_invoices"]) == 0


def test_vat_declaration_monthly_success(logged_in_client, app):
    """Verify monthly VAT calculation and tax optimizer exclusions."""
    _seed_vat_test_invoices(app)

    response = logged_in_client.get("/api/reports/vat-declaration?period_type=monthly&period_value=05&year=2026")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["period_type"] == "monthly"
    assert payload["period_value"] == "05"

    outputs = payload["outputs"]
    # Total Output = SOLD-001 (10M value, 1M tax) + SOLD-002 (5M value, 250k tax)
    assert outputs["total_val"] == 15000000.0
    assert outputs["total_vat"] == 1250000.0
    assert outputs["tax_5_val"] == 5000000.0
    assert outputs["tax_10_val"] == 10000000.0

    inputs = payload["inputs"]
    # Total Inputs = PURCHASE-001 (8M value, 800k tax) + PURCHASE-002 (6M value, 600k tax)
    assert inputs["total_value"] == 14000000.0
    assert inputs["total_vat"] == 1400000.0
    # Deductible VAT by default excludes the cash payment warning invoice (600k), leaving only 800k
    assert inputs["deductible_vat"] == 800000.0

    calculations = payload["calculations"]
    # VAT Payable = Output VAT (1.25M) - Deductible Input VAT (800k) = 450k
    assert calculations["vat_payable"] == 450000.0
    assert calculations["vat_carried_forward"] == 0.0

    # Disputed invoices must list the cash warned invoice
    disputed = payload["disputed_invoices"]
    assert len(disputed) == 1
    assert disputed[0]["id"] == "PURCHASE-002"
    assert disputed[0]["tax_amount"] == 600000.0
    assert "5 triệu VND" in disputed[0]["warning"]


def test_vat_declaration_quarterly_success(logged_in_client, app):
    """Verify quarterly VAT calculation rolls up multiple months in Q2."""
    _seed_vat_test_invoices(app)

    # Q2 comprises months 04, 05, 06
    # Our seed data has:
    # - April: SOLD-003 (20M value, 0% VAT)
    # - May: SOLD-001 (10M value, 10% VAT) and SOLD-002 (5M value, 5% VAT)
    # - May Inputs: PURCHASE-001 (8M, 800k tax) and PURCHASE-002 (6M, 600k tax, excluded by default)
    
    response = logged_in_client.get("/api/reports/vat-declaration?period_type=quarterly&period_value=2&year=2026")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["period_type"] == "quarterly"
    assert payload["period_value"] == "2"

    outputs = payload["outputs"]
    # Total Sales = 20M (April 0%) + 10M (May 10%) + 5M (May 5%) = 35M
    assert outputs["total_val"] == 35000000.0
    assert outputs["tax_0_val"] == 20000000.0
    assert outputs["total_vat"] == 1250000.0

    inputs = payload["inputs"]
    assert inputs["total_value"] == 14000000.0
    assert inputs["deductible_vat"] == 800000.0


def test_vat_declaration_gemma4_ai_warnings(logged_in_client, app):
    """Verify that advanced Gemma-4 AI compliance warnings exclude input invoices from VAT deduction."""
    with app.app_context():
        from invoices.models import AIAuditResult, Invoice, LineItem
        LineItem.query.delete()
        Invoice.query.delete()
        AIAuditResult.query.delete()
        db.session.commit()

        # Seed invoice
        inv = Invoice(
            id="AI-TEST-PURCHASE-1",
            filename="purchase_ai.xml",
            invoice_type="purchase",
            number="0999",
            date="2026-05-20",
            currency="VND",
            seller_mst="0312345678",
            seller_name="CONG TY RỦI RO THUẾ",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=30000000.0,
            tax_amount=3000000.0,
            total_amount=33000000.0,
            has_signature=True,
            payment_method="TM",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv)
        db.session.commit()

        # Add Gemma-4 AI compliance warning
        ai_warning = AIAuditResult(
            invoice_id="AI-TEST-PURCHASE-1",
            warning_type="personal_purchase",
            explanation="Ô tô hạng sang vượt định mức 1.6 tỷ theo Thông tư 219.",
            created_at=datetime.now().isoformat()
        )
        db.session.add(ai_warning)
        db.session.commit()

    response = logged_in_client.get("/api/reports/vat-declaration?period_type=monthly&period_value=05&year=2026")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True

    # Deductible VAT should be 0 since our only purchase has a critical Gemma-4 compliance warning!
    assert payload["inputs"]["total_vat"] == 3000000.0
    assert payload["inputs"]["deductible_vat"] == 0.0

    # It must be reported under disputed_invoices
    disputed = payload["disputed_invoices"]
    assert len(disputed) == 1
    assert disputed[0]["id"] == "AI-TEST-PURCHASE-1"
    assert "personal_purchase" in disputed[0]["warning"]
    assert "vượt định mức 1.6 tỷ" in disputed[0]["warning"]

