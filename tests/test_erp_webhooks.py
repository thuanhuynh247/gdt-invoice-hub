import pytest
import csv
import io
import openpyxl
from unittest.mock import patch, MagicMock
from invoices.models import Invoice, LineItem
from invoices.erp_service import generate_misa_export, generate_odoo_export, WebhookDispatcher, MOCK_SENT_WEBHOOKS
from invoices.scheduler import save_scheduler_settings
from app import create_app
from extensions import db

@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope="function")
def session(app):
    with app.app_context():
        db.session.query(Invoice).delete()
        db.session.commit()
        yield db.session
        db.session.rollback()

def test_generate_misa_export():
    # Build a couple of mock invoices
    inv1 = Invoice(
        id="seller1-A-1",
        date="2026-05-25",
        symbol="A/26E",
        number="0001",
        seller_mst="111111111",
        seller_name="Seller One",
        seller_address="Hanoi",
        payment_method="Chuyển khoản",
        amount_before_tax=1000.0,
        tax_amount=100.0,
        total_amount=1100.0,
        imported_at="2026-05-25T12:00:00"
    )
    
    # Trigger MISA SME Excel generation
    xlsx_bytes = generate_misa_export([inv1])
    assert len(xlsx_bytes) > 0
    
    # Load xlsx using openpyxl to check content
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    sheet = wb.active
    assert sheet.title == "MISA SME Purchase Invoices"
    
    # Row 1 headers
    headers = [cell.value for cell in sheet[1]]
    assert "Ngày hạch toán" in headers
    assert "Mã số thuế người bán" in headers
    
    # Row 2 data
    row2 = [cell.value for cell in sheet[2]]
    assert "25/05/2026" in row2
    assert "111111111" in row2
    assert 1000.0 in row2
    assert 1100.0 in row2

def test_generate_odoo_export():
    inv1 = Invoice(
        id="seller1-A-1",
        date="2026-05-25",
        symbol="A/26E",
        number="0001",
        seller_mst="111111111",
        seller_name="Seller One",
        seller_address="Hanoi",
        payment_method="Chuyển khoản",
        amount_before_tax=1000.0,
        tax_amount=100.0,
        total_amount=1100.0,
        imported_at="2026-05-25T12:00:00"
    )
    
    csv_str = generate_odoo_export([inv1])
    assert len(csv_str) > 0
    
    # Read CSV
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    
    # Check headers
    assert rows[0] == ["ref", "date", "journal_id", "line_ids/account_id", "line_ids/name", "line_ids/debit", "line_ids/credit"]
    
    # Check debit (line 1 - expense)
    assert rows[1][0] == "INV-0001"
    assert rows[1][3] == "642000"
    assert float(rows[1][5]) == 1000.0
    assert float(rows[1][6]) == 0.0
    
    # Check tax line (line 2)
    assert rows[2][3] == "133100"
    assert float(rows[2][5]) == 100.0
    
    # Check credit (line 3 - payable)
    assert rows[3][3] == "112100"  # Bank due to ck
    assert float(rows[3][5]) == 0.0
    assert float(rows[3][6]) == 1100.0

def test_webhook_dispatcher(app):
    MOCK_SENT_WEBHOOKS.clear()
    
    # Mock settings
    save_scheduler_settings({
        "webhook_enabled": True,
        "webhook_url": "https://example.com/webhook",
        "webhook_secret": "my-secret-key"
    })
    
    data = {"invoice_id": "test-123"}
    success = WebhookDispatcher.dispatch_event("invoice.downloaded", data)
    
    assert success is True
    assert len(MOCK_SENT_WEBHOOKS) == 1
    assert MOCK_SENT_WEBHOOKS[0]["event_type"] == "invoice.downloaded"
    assert MOCK_SENT_WEBHOOKS[0]["data"] == data

def test_api_export_endpoints(app, session):
    client = app.test_client()
    
    # Create test invoice
    inv = Invoice(
        id="test-endpoint-1",
        date="2026-05-25",
        symbol="A/26E",
        number="0001",
        seller_mst="111111111",
        seller_name="Seller One",
        amount_before_tax=1000.0,
        tax_amount=100.0,
        total_amount=1100.0,
        imported_at="2026-05-25T12:00:00"
    )
    session.add(inv)
    session.commit()
    
    # Log in mock session
    with client.session_transaction() as sess:
        sess["jwt"] = "mock-jwt-token"
        sess["logged_in"] = True
        
    # Test MISA export endpoint
    resp_misa = client.get("/api/erp/export/misa")
    assert resp_misa.status_code == 200
    assert resp_misa.headers["Content-Disposition"] == "attachment; filename=misa_export.xlsx"
    
    # Test Odoo export endpoint
    resp_odoo = client.get("/api/erp/export/odoo")
    assert resp_odoo.status_code == 200
    assert resp_odoo.headers["Content-Disposition"] == "attachment; filename=odoo_export.csv"


def test_post_invoice_to_erp_misa(app, session):
    from invoices.erp_service import post_invoice_to_erp, MOCK_ERP_POSTS
    MOCK_ERP_POSTS.clear()

    # Save ERP settings
    save_scheduler_settings({
        "erp_enabled": True,
        "erp_type": "misa",
        "erp_api_url": "https://misa-api.example.com/post",
        "erp_auth_token": "my-misa-token"
    })

    inv = Invoice(
        id="test-misa-post-1",
        date="2026-05-25",
        symbol="A/26E",
        number="0002",
        seller_mst="222222222",
        seller_name="Seller Two",
        payment_method="Tiền mặt",
        amount_before_tax=2000.0,
        tax_amount=200.0,
        total_amount=2200.0,
        imported_at="2026-05-25T12:00:00"
    )
    session.add(inv)
    session.commit()

    success = post_invoice_to_erp(inv)
    assert success is True
    assert inv.erp_synced is True
    assert inv.erp_sync_date is not None
    assert inv.erp_sync_error is None

    assert len(MOCK_ERP_POSTS) == 1
    post = MOCK_ERP_POSTS[0]
    assert post["erp_type"] == "misa"
    assert post["url"] == "https://misa-api.example.com/post"
    assert post["payload"]["DebitAccount"] == "1561"
    assert post["payload"]["CreditAccount"] == "1111" # due to Cash/Tiền mặt
    assert post["payload"]["RefNo"] == "A/26E/0002"


def test_post_invoice_to_erp_odoo(app, session):
    from invoices.erp_service import post_invoice_to_erp, MOCK_ERP_POSTS
    MOCK_ERP_POSTS.clear()

    # Save ERP settings
    save_scheduler_settings({
        "erp_enabled": True,
        "erp_type": "odoo",
        "erp_api_url": "https://odoo-api.example.com/post",
        "erp_auth_token": "my-odoo-token"
    })

    inv = Invoice(
        id="test-odoo-post-1",
        date="2026-05-25",
        symbol="B/26E",
        number="0003",
        seller_mst="333333333",
        seller_name="Seller Three",
        payment_method="Chuyển khoản",
        amount_before_tax=3000.0,
        tax_amount=300.0,
        total_amount=3300.0,
        imported_at="2026-05-25T12:00:00"
    )
    session.add(inv)
    session.commit()

    success = post_invoice_to_erp(inv)
    assert success is True
    assert inv.erp_synced is True

    assert len(MOCK_ERP_POSTS) == 1
    post = MOCK_ERP_POSTS[0]
    assert post["erp_type"] == "odoo"
    assert len(post["payload"]["line_ids"]) == 3
    # debit line
    assert post["payload"]["line_ids"][0]["account_id"] == "642000"
    assert post["payload"]["line_ids"][0]["debit"] == 3000.0
    # payable credit line (Bank due to chuyển khoản)
    assert post["payload"]["line_ids"][2]["account_id"] == "112100"


def test_api_post_invoice_to_erp_route(app, session):
    client = app.test_client()

    inv = Invoice(
        id="test-route-post-1",
        date="2026-05-25",
        symbol="C/26E",
        number="0004",
        seller_mst="444444444",
        seller_name="Seller Four",
        payment_method="Chuyển khoản",
        amount_before_tax=4000.0,
        tax_amount=400.0,
        total_amount=4400.0,
        imported_at="2026-05-25T12:00:00"
    )
    session.add(inv)
    session.commit()

    # Unauthorized check
    res = client.post(f"/api/invoices/{inv.id}/post-erp")
    assert res.status_code == 401

    # Login as viewer (no access)
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "viewer"
        sess["user_role"] = "viewer"
        sess["expires_at"] = "2099-05-20T00:00:00+00:00"
    res = client.post(f"/api/invoices/{inv.id}/post-erp")
    assert res.status_code == 403

    # Login as admin
    with client.session_transaction() as sess:
        sess["user_role"] = "admin"
    save_scheduler_settings({
        "erp_enabled": True,
        "erp_type": "misa",
        "erp_api_url": "https://misa-api.example.com/post",
        "erp_auth_token": "token"
    })
    res = client.post(f"/api/invoices/{inv.id}/post-erp")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["erp_synced"] is True

