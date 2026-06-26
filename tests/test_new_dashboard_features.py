"""
Tests for new dashboard endpoints:
1. /api/invoices/expense-categories (AI Expense Chart)
2. /api/invoices/validate-xml (XML Pre-issuance Validator with GDT error code explainer)
"""

from __future__ import annotations
import json
import pytest
from io import BytesIO
from extensions import db
from invoices.models import Invoice, LineItem
from invoices.thread_local import set_current_thread_mst, clear_thread_local_context

@pytest.fixture
def sample_data(app):
    with app.app_context():
        set_current_thread_mst("0908070605")
        try:
            LineItem.query.delete()
            Invoice.query.delete()
            db.session.commit()

            invoice = Invoice(
                id="INV-DASH-1",
                number="1111",
                date="2026-06-01",
                seller_name="Seller A",
                seller_mst="0102030405",
                buyer_name="Buyer B",
                buyer_mst="0908070605",
                amount_before_tax=500000.0,
                tax_amount=50000.0,
                total_amount=550000.0,
                taxpayer_mst="0908070605", # active taxpayer MST (Buyer B is taxpayer)
                imported_at="2026-06-01 10:00:00",
                updated_at="2026-06-01 10:00:00",
                import_status="imported"
            )
            db.session.add(invoice)

            item1 = LineItem(
                id=1001,
                invoice_id="INV-DASH-1",
                item_name="Bút bi Thiên Long",
                quantity=10,
                unit_price=5000.0,
                amount_before_tax=50000.0,
                tax_amount=5000.0,
                amount_after_tax=55000.0,
                expense_category="Văn phòng phẩm & Thiết bị văn phòng"
            )
            item2 = LineItem(
                id=1002,
                invoice_id="INV-DASH-1",
                item_name="Grab giao hàng",
                quantity=1,
                unit_price=20000.0,
                amount_before_tax=20000.0,
                tax_amount=2000.0,
                amount_after_tax=22000.0,
                expense_category="Vận chuyển, Giao hàng & Logistics"
            )
            db.session.add(item1)
            db.session.add(item2)
            db.session.commit()
        finally:
            clear_thread_local_context()

def test_api_expense_categories(logged_in_client, sample_data):
    # Set session variable for active taxpayer and tax_code
    with logged_in_client.session_transaction() as sess:
        sess["active_taxpayer_mst"] = "0908070605"
        sess["tax_code"] = "0908070605"

    resp = logged_in_client.get("/api/invoices/expense-categories")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    categories = {x["category"]: x["amount"] for x in data}
    assert "Văn phòng phẩm & Thiết bị văn phòng" in categories
    assert categories["Văn phòng phẩm & Thiết bị văn phòng"] == 55000.0
    assert "Vận chuyển, Giao hàng & Logistics" in categories
    assert categories["Vận chuyển, Giao hàng & Logistics"] == 22000.0

def test_validate_xml_valid(logged_in_client):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <HDon>
        <DLHDon>
            <TTChung>
                <KHMSHDon>1</KHMSHDon>
                <KHHDon>C26TAA</KHHDon>
                <SHDon>0001234</SHDon>
                <NLap>2026-06-25</NLap>
            </TTChung>
            <NDHDon>
                <NBan>
                    <Ten>CONG TY TNHH ABC</Ten>
                    <MST>0110223344</MST>
                </NBan>
                <NMua>
                    <Ten>CONG TY TNHH XYZ</Ten>
                    <MST>0220334455</MST>
                </NMua>
                <TToan>
                    <TgTCThue>1000000</TgTCThue>
                    <TgTThue>100000</TgTThue>
                    <TgTTTBangChu>Mot trieu mot tram nghin dong</TgTTTBangChu>
                </TToan>
            </NDHDon>
        </DLHDon>
        <Signature>SomeDigitalSignatureBytes</Signature>
    </HDon>
    """
    data = {
        'file': (BytesIO(xml_content.encode('utf-8')), 'valid_invoice.xml')
    }
    resp = logged_in_client.post(
        "/api/invoices/validate-xml",
        data=data,
        content_type='multipart/form-data'
    )
    assert resp.status_code == 200
    res_data = resp.get_json()
    assert res_data["valid"] is True
    assert "metadata" in res_data
    assert res_data["metadata"]["invoice_number"] == "0001234"
    assert res_data["metadata"]["seller_mst"] == "0110223344"

def test_validate_xml_invalid(logged_in_client):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <HDon>
        <DLHDon>
            <TTChung>
                <KHMSHDon>1</KHMSHDon>
                <KHHDon>C26TAA</KHHDon>
                <SHDon></SHDon>
                <NLap>2026-06-25</NLap>
            </TTChung>
            <NDHDon>
                <TToan>
                    <TgTCThue>1000000</TgTCThue>
                    <TgTThue>100000</TgTThue>
                </TToan>
            </NDHDon>
        </DLHDon>
    </HDon>
    """
    data = {
        'file': (BytesIO(xml_content.encode('utf-8')), 'invalid_invoice.xml')
    }
    resp = logged_in_client.post(
        "/api/invoices/validate-xml",
        data=data,
        content_type='multipart/form-data'
    )
    assert resp.status_code == 200
    res_data = resp.get_json()
    assert res_data["valid"] is False
    assert len(res_data["errors"]) > 0
    
    error_codes = [err["code"] for err in res_data["errors"]]
    assert "XML-002" in error_codes
