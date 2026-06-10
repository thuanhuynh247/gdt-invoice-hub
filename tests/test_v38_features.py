import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from invoices.models import Invoice, LineItem, DeliveryNote, LogisticsAllocation, TaxpayerProfile
from invoices.v38_service import DeliveryNoteService, LogisticsCostAllocatorService

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.app_context():
        db.create_all()
        
        # Seed taxpayer profiles to avoid foreign key constraint issues
        tp1 = TaxpayerProfile(
            mst="0102030405",
            company_name="Cong ty Giao nhan Antigravity",
            gdt_username="antigravity_tax",
            gdt_password_encrypted="encrypted_pwd",
            created_at="2026-01-01"
        )
        tp2 = TaxpayerProfile(
            mst="0908070605",
            company_name="Nha ban hang Target",
            gdt_username="target_tax",
            gdt_password_encrypted="encrypted_pwd",
            created_at="2026-01-01"
        )
        db.session.add(tp1)
        db.session.add(tp2)
        db.session.commit()
        
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_delivery_note_parsing(client):
    # Test GDT XML format
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <HDon>
        <soPhieu>PXK-9999123</soPhieu>
        <ngayLap>2026-06-01</ngayLap>
        <mstNguoiGui>0102030405</mstNguoiGui>
        <mstNguoiNhan>0908070605</mstNguoiNhan>
        <hdVanChuyen>HDVC-KHO-01</hdVanChuyen>
        <tongTien>15000000</tongTien>
    </HDon>"""

    parsed = DeliveryNoteService.parse_delivery_note_xml(xml_data)
    assert parsed["note_number"] == "PXK-9999123"
    assert parsed["note_date"] == "2026-06-01"
    assert parsed["sender_mst"] == "0102030405"
    assert parsed["receiver_mst"] == "0908070605"
    assert parsed["transport_contract"] == "HDVC-KHO-01"
    assert parsed["total_value"] == 15000000.0


def test_delivery_note_invoice_matching(client):
    # Setup delivery note
    dn = DeliveryNote(
        note_number="PXK-MATCH-01",
        note_date="2026-06-01",
        sender_mst="0102030405",
        receiver_mst="0908070605",
        total_value=10000000.0
    )
    db.session.add(dn)

    # Setup invoice matching MSTs, date after delivery note, matching total_amount
    inv = Invoice(
        id="INV-MATCH-01",
        number="INV-001",
        imported_at="2026-06-05",
        taxpayer_mst="0102030405",
        buyer_mst="0908070605",
        total_amount=10000000.0,
        is_cancelled=False,
        import_status="imported"
    )
    db.session.add(inv)
    db.session.commit()

    matched = DeliveryNoteService.auto_match_invoice(dn)
    assert matched is not None
    assert matched.id == "INV-MATCH-01"


def test_timing_penalty_calculations(client):
    dn = DeliveryNote(note_number="PXK-TIME-1", note_date="2026-06-01")
    
    # 1. Compliance case (within 10 days)
    inv_compliant = Invoice(id="INV-COMP", imported_at="2026-06-08", taxpayer_mst="0102030405", import_status="imported")
    res1 = DeliveryNoteService.calculate_timing_penalty(dn, inv_compliant)
    assert res1["days_elapsed"] == 7
    assert res1["is_violating"] is False
    assert res1["risk_level"] == "Low"

    # 2. Mild violation (11-15 days)
    inv_mild = Invoice(id="INV-MILD", imported_at="2026-06-14", taxpayer_mst="0102030405", import_status="imported")
    res2 = DeliveryNoteService.calculate_timing_penalty(dn, inv_mild)
    assert res2["days_elapsed"] == 13
    assert res2["is_violating"] is True
    assert "2,000,000" in res2["penalty_range"]
    assert res2["risk_level"] == "Medium"

    # 3. Severe violation (> 30 days)
    inv_severe = Invoice(id="INV-SEV", imported_at="2026-07-15", taxpayer_mst="0102030405", import_status="imported")
    res3 = DeliveryNoteService.calculate_timing_penalty(dn, inv_severe)
    assert res3["days_elapsed"] == 44
    assert res3["is_violating"] is True
    assert "10,000,000" in res3["penalty_range"]
    assert res3["risk_level"] == "Critical"


def test_logistics_invoice_classification(client):
    # Create logistics invoice with matching line-item name
    inv = Invoice(id="INV-LOG-1", taxpayer_mst="0102030405", is_cancelled=False, imported_at="2026-06-01", import_status="imported")
    db.session.add(inv)
    
    item = LineItem(
        invoice_id="INV-LOG-1",
        item_name="Cước vận chuyển hàng hóa từ Hải Phòng về Hà Nội",
        amount_before_tax=5000000.0,
        tax_amount=500000.0
    )
    db.session.add(item)
    db.session.commit()

    is_log = LogisticsCostAllocatorService.is_logistics_invoice(inv)
    assert is_log is True


def test_logistics_allocation_and_valuation(client):
    # Setup Logistics invoice
    log_inv = Invoice(
        id="INV-LOG-01",
        taxpayer_mst="0102030405",
        buyer_mst="0908070605",
        total_amount=2000000.0,
        is_cancelled=False,
        imported_at="2026-06-06",
        import_status="imported"
    )
    db.session.add(log_inv)
    log_item = LineItem(
        invoice_id="INV-LOG-01",
        item_name="Cước phí vận chuyển",
        amount_before_tax=2000000.0,
        tax_amount=200000.0
    )
    db.session.add(log_item)

    # Setup purchase invoices
    p1 = Invoice(
        id="PUR-01",
        taxpayer_mst="0102030405",
        buyer_mst="0908070605",
        total_amount=10000000.0,
        imported_at="2026-06-05",
        is_cancelled=False,
        import_status="imported"
    )
    p2 = Invoice(
        id="PUR-02",
        taxpayer_mst="0102030405",
        buyer_mst="0908070605",
        total_amount=30000000.0,
        imported_at="2026-06-08",
        is_cancelled=False,
        import_status="imported"
    )
    db.session.add(p1)
    db.session.add(p2)

    item1 = LineItem(
        invoice_id="PUR-01",
        item_name="Thép tấm cuộn",
        quantity=2,
        amount_before_tax=10000000.0,
        tax_amount=1000000.0
    )
    item2 = LineItem(
        invoice_id="PUR-02",
        item_name="Ốc vít công nghiệp",
        quantity=100,
        amount_before_tax=30000000.0,
        tax_amount=3000000.0
    )
    db.session.add(item1)
    db.session.add(item2)
    db.session.commit()

    # Verify eligibility search (should return both as they are within +/- 15 days of dummy date window)
    eligible = LogisticsCostAllocatorService.find_eligible_purchase_invoices(log_inv)
    assert len(eligible) == 2

    # Execute Value-Ratio allocation
    alloc_res = LogisticsCostAllocatorService.allocate_logistics_cost("INV-LOG-01", ["PUR-01", "PUR-02"], method="value_ratio")
    assert alloc_res["status"] == "success"
    
    # Total logistics is 2,000,000. PUR-01 is 10M, PUR-02 is 30M (total 40M value).
    # P1 gets 10/40 = 25% = 500,000.
    # P2 gets 30/40 = 75% = 1,500,000.
    allocations = LogisticsAllocation.query.filter_by(logistics_invoice_id="INV-LOG-01").all()
    assert len(allocations) == 2
    
    p1_alloc = next(a for a in allocations if a.purchase_invoice_id == "PUR-01")
    p2_alloc = next(a for a in allocations if a.purchase_invoice_id == "PUR-02")
    assert abs(p1_alloc.allocated_amount - 500000.0) < 0.01
    assert abs(p2_alloc.allocated_amount - 1500000.0) < 0.01

    # Check Adjusted Valuation Report per VAS 02 rules
    val_report = LogisticsCostAllocatorService.get_adjusted_inventory_valuation("0102030405")
    assert val_report["total_original_value"] == 40000000.0
    assert val_report["total_adjusted_value"] == 42000000.0
    
    steel_item = next(item for item in val_report["items"] if "Thép" in item["item_name"])
    assert steel_item["original_total_cost"] == 10000000.0
    assert steel_item["allocated_logistics"] == 500000.0
    assert steel_item["adjusted_unit_cost"] == 5250000.0  # (10M + 500k) / 2 quantity = 5.25M


def test_api_routes_unauthorized(client):
    # Without logged_in session, endpoints should redirect or fail with 401
    res = client.get("/v38-delivery-reconciliation")
    assert res.status_code == 302 # Redirect to login

    res2 = client.get("/api/v38/delivery-notes")
    assert res2.status_code == 401
