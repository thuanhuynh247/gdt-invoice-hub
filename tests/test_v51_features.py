"""Pytest verification suite for v51 Tax Administration Law Amendments 108/2025/QH15.

Tests XML digital signature compliance, foreign vendor B2B withholding calculations,
GDT registration tracking, API routing, views, and database isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v51_service import V51ComplianceService


@pytest.fixture
def mock_app():
    """Create a mock Flask app context with base configurations."""
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["BASE_DATA_DIR"] = os.path.join(os.path.dirname(__file__), "..", "data")

    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    return app


@pytest.fixture
def mock_tenant_db():
    """Ensure a clean tenant DB for testing."""
    mst = "0102030490"
    db_path = get_tenant_db_path(mst)

    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass

    bootstrap_tenant_db(mst)
    yield mst

    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_signature_auditing(mock_tenant_db):
    """Test electronic signature certificate expiry and transmission delay checks."""
    mst = mock_tenant_db
    service = V51ComplianceService()

    # Case 1: Compliant within 24 hours
    res1 = service.audit_etransaction_signature(
        mst, "INV-2026-001", "2026-07-01 10:00:00", "2026-07-01 12:30:00", "2028-12-31 23:59:59"
    )
    assert res1["signature_status"] == "COMPLIANT"
    assert res1["transmission_delay_hours"] == 2.5

    # Case 2: Expired signature
    res2 = service.audit_etransaction_signature(
        mst, "INV-2026-002", "2026-07-01 10:00:00", "2026-07-01 12:30:00", "2025-12-31 23:59:59"
    )
    assert res2["signature_status"] == "SIGNATURE_EXPIRED"

    # Case 3: Transmission delay exceeding 24 hours
    res3 = service.audit_etransaction_signature(
        mst, "INV-2026-003", "2026-07-01 10:00:00", "2026-07-02 15:30:00", "2028-12-31 23:59:59"
    )
    assert res3["signature_status"] == "LATE_TRANSMISSION"
    assert res3["transmission_delay_hours"] == 29.5


def test_foreign_vendor_registration(mock_tenant_db):
    """Test GDT NTNN portal registration status updates."""
    mst = mock_tenant_db
    service = V51ComplianceService()

    res = service.register_foreign_vendor(mst, "Meta Platforms", "999888777", "ACTIVE")
    assert res["vendor_name"] == "Meta Platforms"
    assert res["portal_mst"] == "999888777"
    assert res["registration_status"] == "ACTIVE"


def test_ecommerce_b2b_withholding(mock_tenant_db):
    """Test e-commerce B2B withholding calculations."""
    mst = mock_tenant_db
    service = V51ComplianceService()

    # Case 1: Vendor is registered directly on GDT NTNN portal -> No withholding required
    res1 = service.calculate_ecommerce_withholding(mst, "Google Ireland", True, 200_000_000, 100_000_000)
    assert res1["vat_withholding"] == 0.0
    assert res1["cit_withholding"] == 0.0
    assert res1["total_withholding"] == 0.0

    # Case 2: Vendor is unregistered -> Withholding is mandatory
    # Services: 200M. VAT 5% (10M), CIT 5% (10M)
    # Goods: 100M. VAT 5% (5M), CIT 1% (1M)
    # VAT withholding = 15M, CIT withholding = 11M, Total = 26M
    res2 = service.calculate_ecommerce_withholding(mst, "Netflix Inc", False, 200_000_000, 100_000_000)
    assert res2["vat_withholding"] == 15_000_000
    assert res2["cit_withholding"] == 11_000_000
    assert res2["total_withholding"] == 26_000_000


def test_api_routes_v51(mock_app, mock_tenant_db):
    """Test v51 HTTP API routes and view rendering."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v51-compliance-hub")
    assert res_page.status_code == 200
    assert b"Law 108" in res_page.data or b"Tax Administration" in res_page.data

    res_api = client.get(f"/api/v51/compliance-data?mst={mock_tenant_db}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "signature_audit" in data
    assert "withholding_calculation" in data
