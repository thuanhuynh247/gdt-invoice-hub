"""Pytest verification suite for HAT AI Smart Invoice Adjustment & Correction Hub:
1. Render tax adjustments page.
2. Generate pre-populated adjustment agreement data from invoice ID.
3. Simulate digital signing and GDT 04/SS-HĐĐT submission with database status updates.
4. HAT ERP (MISA compatible) Excel exporting.
"""

from __future__ import annotations

import json
import pytest
from flask import Flask
from extensions import db
from unittest.mock import patch, MagicMock
from invoices.models import Invoice

@pytest.fixture
def mock_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def test_tax_adjustments_page_requires_login(mock_app):
    client = mock_app.test_client()
    res = client.get("/tax-adjustments")
    assert res.status_code == 302  # Redirects to login


def test_tax_adjustments_page_renders_with_flagged_invoices(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["active_taxpayer_mst"] = "0102030499"

    with mock_app.app_context():
        # Seed an invoice with a late signing date warning to flag it
        inv = Invoice(
            id="inv-flagged-1",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="1234567890",
            seller_name="Nha Ban A",
            amount_before_tax=1000000.0,
            tax_amount=100000.0,
            total_amount=1100000.0,
            payment_method="Chuyển khoản",
            date="2026-06-01",
            signing_date="2026-06-26",  # Late signing
            imported_at="2026-06-26T00:00:00"
        )
        db.session.add(inv)
        db.session.commit()

    res = client.get("/tax-adjustments")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "HAT AI Smart" in html
    assert "inv-flagged-1" in html
    assert "Nha Ban A" in html


def test_api_tax_adjustments_generate(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "ke_toan_hat"

    with mock_app.app_context():
        inv = Invoice(
            id="inv-flagged-2",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="9876543210",
            seller_name="Nha Ban B",
            buyer_mst="0102030499",
            buyer_name="Nha Mua A",
            amount_before_tax=2000000.0,
            tax_amount=200000.0,
            total_amount=2200000.0,
            payment_method="Chuyển khoản",
            date="2026-06-26",
            signing_date="2026-06-26",
            imported_at="2026-06-26T00:00:00"
        )
        db.session.add(inv)
        db.session.commit()

    payload = {"invoice_id": "inv-flagged-2"}
    res = client.post("/api/tax/adjustments/generate", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["invoice_id"] == "inv-flagged-2"
    assert data["seller_name"] == "Nha Ban B"
    assert data["buyer_name"] == "Nha Mua A"
    assert data["total_amount"] == 2200000.0
    assert data["representative_b"] == "ke_toan_hat"


def test_api_tax_adjustments_submit_gdt_updates_db(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    with mock_app.app_context():
        inv = Invoice(
            id="inv-flagged-3",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="9876543210",
            seller_name="Nha Ban B",
            amount_before_tax=2000000.0,
            tax_amount=200000.0,
            total_amount=2200000.0,
            payment_method="Chuyển khoản",
            date="2026-06-26",
            signing_date="2026-06-26",
            imported_at="2026-06-26T00:00:00",
            invoice_status="Chờ xử lý"
        )
        db.session.add(inv)
        db.session.commit()

    payload = {"invoice_id": "inv-flagged-3"}
    res = client.post("/api/tax/adjustments/submit-gdt", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["status"] == "success"
    assert "gdt_transaction_id" in data
    assert data["invoice_status"] == "Đã điều chỉnh (CQT chấp nhận)"

    # Verify database update
    with mock_app.app_context():
        updated_inv = db.session.get(Invoice, "inv-flagged-3")
        assert updated_inv.invoice_status == "Đã điều chỉnh (CQT chấp nhận)"
        assert "GDT-" in updated_inv.notes


def test_api_erp_export_hat(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    with mock_app.app_context():
        inv = Invoice(
            id="inv-export-1",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="1234567890",
            seller_name="Nha Ban A",
            amount_before_tax=1000000.0,
            tax_amount=100000.0,
            total_amount=1100000.0,
            payment_method="Chuyển khoản",
            date="2026-06-26",
            signing_date="2026-06-26",
            imported_at="2026-06-26T00:00:00"
        )
        db.session.add(inv)
        db.session.commit()

    res = client.get("/api/erp/export/hat-erp")
    assert res.status_code == 200
    assert res.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in res.headers["Content-Disposition"]
    assert "hat_erp_export.xlsx" in res.headers["Content-Disposition"]
