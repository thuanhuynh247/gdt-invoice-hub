"""Pytest verification suite for v56 License Fee (LF) Decree 139/2016/NĐ-CP.

Verifies correct license fee calculations based on charter capital brackets for enterprises,
annual revenue brackets for households, flat fee rates for branches/offices, exemptions for
newly established entities/agricultural cooperatives, and REST JSON API endpoints.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v56_service import V56ComplianceService


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
    mst = "0102030496"
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


def test_license_fee_calculation(mock_tenant_db):
    """Test calculations and exemptions for various organization and household types."""
    mst = mock_tenant_db
    service = V56ComplianceService()

    # Enterprise with charter capital > 10 Billion VND
    res = service.calculate_license_fee(mst, "HQ Headquarters", "enterprise", 15000000000.0, 0.0, False, False)
    assert res["standard_fee"] == 3000000.0
    assert res["effective_fee"] == 3000000.0
    assert res["is_exempt"] is False

    # Enterprise with charter capital <= 10 Billion VND
    res = service.calculate_license_fee(mst, "Small Tech Ltd", "enterprise", 5000000000.0, 0.0, False, False)
    assert res["standard_fee"] == 2000000.0
    assert res["effective_fee"] == 2000000.0
    assert res["is_exempt"] is False

    # Branch Office (Flat 1M VND)
    res = service.calculate_license_fee(mst, "Hanoi Branch", "branch", 0.0, 0.0, False, False)
    assert res["standard_fee"] == 1000000.0
    assert res["effective_fee"] == 1000000.0
    assert res["is_exempt"] is False

    # Newly Established First Calendar Year Exemption
    res = service.calculate_license_fee(mst, "New Startup LLC", "enterprise", 3000000000.0, 0.0, True, False)
    assert res["standard_fee"] == 2000000.0
    assert res["effective_fee"] == 0.0
    assert res["is_exempt"] is True
    assert "First calendar year" in res["exemption_reason"]

    # Agricultural Cooperative Exemption
    res = service.calculate_license_fee(mst, "Agri Coop A", "enterprise", 2000000000.0, 0.0, False, True)
    assert res["effective_fee"] == 0.0
    assert res["is_exempt"] is True
    assert "Agricultural cooperative" in res["exemption_reason"]

    # Household Business: Revenue > 500M VND
    res = service.calculate_license_fee(mst, "Store A", "household", 0.0, 600000000.0, False, False)
    assert res["standard_fee"] == 1000000.0
    assert res["effective_fee"] == 1000000.0
    assert res["is_exempt"] is False

    # Household Business: Revenue > 300M <= 500M VND
    res = service.calculate_license_fee(mst, "Store B", "household", 0.0, 400000000.0, False, False)
    assert res["standard_fee"] == 500000.0
    assert res["effective_fee"] == 500000.0
    assert res["is_exempt"] is False

    # Household Business: Revenue > 100M <= 300M VND
    res = service.calculate_license_fee(mst, "Store C", "household", 0.0, 200000000.0, False, False)
    assert res["standard_fee"] == 300000.0
    assert res["effective_fee"] == 300000.0
    assert res["is_exempt"] is False

    # Household Business: Revenue <= 100M VND (Exempt)
    res = service.calculate_license_fee(mst, "Store D", "household", 0.0, 50000000.0, False, False)
    assert res["effective_fee"] == 0.0
    assert res["is_exempt"] is True
    assert "Low annual revenue" in res["exemption_reason"]


def test_api_routes_v56(mock_app, mock_tenant_db):
    """Test V56 endpoints, template render, and database records extraction."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # GET compliance hub UI
    res_page = client.get("/v56-compliance-hub")
    assert res_page.status_code == 200
    assert b"License Fee Compliance" in res_page.data or b"Decree 139/2016" in res_page.data

    # POST calculation
    res_calc = client.post("/api/v56/calculate", json={
        "mst": mock_tenant_db,
        "entity_name": "Test Company",
        "entity_type": "enterprise",
        "charter_capital": 25000000000.0,
        "annual_revenue": 0.0,
        "is_newly_established": False,
        "is_agri_cooperative": False
    })
    assert res_calc.status_code == 200
    data_calc = json.loads(res_calc.data)
    assert data_calc["status"] == "success"
    assert data_calc["results"]["effective_fee"] == 3000000.0

    # GET baseline compliance data
    res_data = client.get(f"/api/v56/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "enterprise_large" in data
    assert "branch_flat" in data
    assert "new_exemption" in data
    assert "household_medium" in data
    assert len(data["history"]) > 0
