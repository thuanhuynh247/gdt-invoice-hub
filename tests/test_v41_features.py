import pytest
from datetime import datetime
from extensions import db
from invoices.models import Invoice, ExportCustomsDeclaration, ExportDeclarationInvoiceMatch, VatRefundApplication
from invoices.v41_service import ExportVatRefundService

@pytest.fixture(autouse=True)
def setup_test_data(app):
    with app.app_context():
        # Setup clean test data
        db.create_all()
        
        # Create a mock invoice for matching
        inv1 = Invoice(
            id="0102030405-AB-12345",
            filename="inv1.xml",
            invoice_type="purchase",
            template_code="01GTKT",
            symbol="AB/26E",
            number="12345",
            date="2026-06-11",
            seller_mst="0908070605",
            seller_name="Export Supplier Co",
            buyer_mst="0102030405",
            buyer_name="Viet taxpayer corp",
            amount_before_tax=250000000.0,
            tax_amount=0.0,
            total_amount=250000000.0,  # 250M VND
            payment_method="Chuyển khoản",
            taxpayer_mst="0102030405",
            imported_at="2026-06-11 00:00:00"
        )
        db.session.add(inv1)
        db.session.commit()
        
        yield
        
        # Cleanup
        db.session.remove()
        db.drop_all()


def test_customs_declaration_parser(client):
    """US-530: Verify XML uploader extracts declaration values and clearance dates."""
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <declaration>
        <so_to_khai>CD-2026-999</so_to_khai>
        <ngay_dang_ky>2026-06-01</ngay_dang_ky>
        <ngay_thong_quan>2026-06-11</ngay_thong_quan>
        <tri_gia_usd>10000.00</tri_gia_usd>
        <ty_gia>25000.00</ty_gia>
        <tri_gia_vnd>250000000.00</tri_gia_vnd>
        <ma_hs>8471.30.10</ma_hs>
    </declaration>
    """
    res = ExportVatRefundService.parse_customs_xml(xml_data, "0102030405")
    
    assert res["declaration_num"] == "CD-2026-999"
    assert res["registration_date"] == "2026-06-01"
    assert res["clearance_date"] == "2026-06-11"
    assert res["export_value_usd"] == 10000.0
    assert res["exchange_rate"] == 25000.0
    assert res["export_value_vnd"] == 250000000.0
    assert res["hs_codes"] == "8471.30.10"
    assert res["status"] == "Pending"


def test_customs_invoice_matcher(client):
    """US-531: Verify customs declarations match with corresponding export invoices."""
    # First, insert a parsed customs declaration
    decl = ExportCustomsDeclaration(
        declaration_num="CD-2026-101",
        registration_date="2026-06-01",
        clearance_date="2026-06-11",
        taxpayer_mst="0102030405",
        export_value_usd=10000.0,
        exchange_rate=25000.0,
        export_value_vnd=250000000.0,  # Matches total_amount of inv1
        hs_codes="8471.30.10",
        status="Pending"
    )
    db.session.add(decl)
    db.session.commit()
    
    matches = ExportVatRefundService.reconcile_declarations("0102030405")
    assert len(matches) == 1
    assert matches[0]["declaration_num"] == "CD-2026-101"
    assert matches[0]["status"] == "matched"
    assert matches[0]["value_difference"] == 0.0
    
    # Verify declaration status updated
    updated_decl = ExportCustomsDeclaration.query.get(decl.id)
    assert updated_decl.status == "Reconciled"


def test_form_01_1_gtgt_builder(client):
    """US-532: Verify Circular 80 Form 01-1/GTGT list displays correct export details."""
    decl = ExportCustomsDeclaration(
        declaration_num="CD-2026-202",
        registration_date="2026-06-01",
        clearance_date="2026-06-11",
        taxpayer_mst="0102030405",
        export_value_usd=10000.0,
        exchange_rate=25000.0,
        export_value_vnd=250000000.0,
        hs_codes="8471.30.10",
        status="Pending"
    )
    db.session.add(decl)
    db.session.commit()
    
    # Run reconciliation to create match
    ExportVatRefundService.reconcile_declarations("0102030405")
    
    form_data = ExportVatRefundService.build_form_01_1_gtgt("0102030405", "2026-06-01", "2026-06-30")
    assert len(form_data) == 1
    assert form_data[0]["customs_num"] == "CD-2026-202"
    assert form_data[0]["invoice_number"] == "12345"
    assert form_data[0]["export_value_vnd"] == 250000000.0
    assert form_data[0]["tax_rate"] == "0%"


def test_form_01_dnht_wizard(client):
    """US-533: Verify Form 01/ĐNHT calculations and submission constraints."""
    # Reconciled export setup
    decl = ExportCustomsDeclaration(
        declaration_num="CD-2026-303",
        registration_date="2026-06-01",
        clearance_date="2026-06-11",
        taxpayer_mst="0102030405",
        export_value_usd=10000.0,
        exchange_rate=25000.0,
        export_value_vnd=2500000000.0,  # 2.5 billion VND
        hs_codes="8471.30.10",
        status="Reconciled"
    )
    db.session.add(decl)
    db.session.commit()
    
    # Limit check: Input VAT = 100M VND, export revenue = 2.5B VND (10% = 250M VND limit)
    # Allowed refund amount should be 100M VND.
    limits = ExportVatRefundService.calculate_refund_limits("0102030405", "2026-06-01", "2026-06-30", 100000000.0)
    assert limits["total_export_revenue"] == 2500000000.0
    assert limits["max_refund_by_revenue"] == 250000000.0
    assert limits["allowed_refund_amount"] == 100000000.0
    assert limits["min_threshold_passed"] is False  # Under 300 million VND limit
    
    # Try with Input VAT = 350M VND. Allowed refund = min(350M, 250M) = 250M VND.
    limits2 = ExportVatRefundService.calculate_refund_limits("0102030405", "2026-06-01", "2026-06-30", 350000000.0)
    assert limits2["allowed_refund_amount"] == 250000000.0
    assert limits2["min_threshold_passed"] is True
    
    # Submit a valid request
    app_dict = ExportVatRefundService.submit_refund_application(
        "0102030405", "2026-06-01", "2026-06-30", 350000000.0, 200000000.0
    )
    assert app_dict["refund_requested_amount"] == 200000000.0
    assert app_dict["status"] == "Submitted"


def test_refund_dashboard_rendering(client):
    """US-534: Verify dashboard statistics collection and compliance checks."""
    stats = ExportVatRefundService.get_refund_dashboard_data("0102030405")
    assert "total_declarations" in stats
    assert "reconciled_declarations" in stats
    assert "compliance_rate" in stats
    assert stats["compliance_rate"] == 100.0  # payment method is 'Chuyển khoản'
