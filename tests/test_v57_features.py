"""Pytest verification suite for v57 Registration Fee (RF) Decree 10/2022/NĐ-CP.

Verifies correct registration fee calculations for real estate (0.5%), cars (2%-12%),
motorbikes (2%-5%), yachts/aircraft (1%), exemptions for agricultural land, diplomatic
assets, merit family housing, and REST JSON API endpoints.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v57_service import V57ComplianceService


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
    mst = "0102030497"
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


def test_rf_real_estate(mock_tenant_db):
    """Test real estate registration fee at 0.5%."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Apartment Vinhomes", "real_estate", 5000000000.0
    )
    assert res["rate_pct"] == 0.5
    assert res["registration_fee"] == 25000000.0
    assert res["effective_fee"] == 25000000.0
    assert res["is_exempt"] is False


def test_rf_car_standard_province(mock_tenant_db):
    """Test car first-time registration at 2% in standard provinces."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Toyota Camry", "car", 1200000000.0,
        province="standard", is_first_registration=True
    )
    assert res["rate_pct"] == 2.0
    assert res["registration_fee"] == 24000000.0
    assert res["is_exempt"] is False


def test_rf_car_hanoi_first_registration(mock_tenant_db):
    """Test car first-time registration at 12% in Hanoi."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Mercedes S-Class", "car", 3000000000.0,
        province="hanoi", is_first_registration=True
    )
    assert res["rate_pct"] == 12.0
    assert res["registration_fee"] == 360000000.0
    assert res["is_exempt"] is False


def test_rf_car_subsequent_registration(mock_tenant_db):
    """Test car subsequent registration at 2%."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Honda Civic Used", "car", 800000000.0,
        province="hanoi", is_first_registration=False
    )
    assert res["rate_pct"] == 2.0
    assert res["registration_fee"] == 16000000.0


def test_rf_motorbike_large(mock_tenant_db):
    """Test motorbike >175cc at 5%."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Honda CBR600", "motorbike", 280000000.0,
        cylinder_capacity=600
    )
    assert res["rate_pct"] == 5.0
    assert res["registration_fee"] == 14000000.0


def test_rf_motorbike_small(mock_tenant_db):
    """Test motorbike ≤175cc at 2%."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Honda Wave", "motorbike", 30000000.0,
        cylinder_capacity=110
    )
    assert res["rate_pct"] == 2.0
    assert res["registration_fee"] == 600000.0


def test_rf_yacht(mock_tenant_db):
    """Test yacht/watercraft at 1%."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Luxury Yacht", "yacht", 50000000000.0
    )
    assert res["rate_pct"] == 1.0
    assert res["registration_fee"] == 500000000.0


def test_rf_agricultural_land_exemption(mock_tenant_db):
    """Test agricultural land exemption."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Rice Paddy Field", "land", 2000000000.0,
        is_agricultural_land=True
    )
    assert res["is_exempt"] is True
    assert res["effective_fee"] == 0.0
    assert "Agricultural" in res["exemption_reason"]


def test_rf_diplomatic_exemption(mock_tenant_db):
    """Test diplomatic asset exemption."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Embassy Vehicle", "car", 2000000000.0,
        is_diplomatic=True
    )
    assert res["is_exempt"] is True
    assert res["effective_fee"] == 0.0
    assert "diplomatic" in res["exemption_reason"]


def test_rf_merit_family_housing_exemption(mock_tenant_db):
    """Test revolutionary merit family housing exemption."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    res = service.calculate_registration_fee(
        mst, "Merit Family House", "real_estate", 1500000000.0,
        is_merit_family_housing=True
    )
    assert res["is_exempt"] is True
    assert res["effective_fee"] == 0.0
    assert "merit" in res["exemption_reason"].lower()


def test_rf_history(mock_tenant_db):
    """Test history retrieval after calculations."""
    mst = mock_tenant_db
    service = V57ComplianceService()

    service.calculate_registration_fee(mst, "Test Asset", "car", 1000000000.0)
    history = service.get_history(mst)
    assert len(history) >= 1
    assert history[0]["asset_description"] == "Test Asset"


def test_api_routes_v57(mock_app, mock_tenant_db):
    """Test V57 endpoints, template render, and database records."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # GET compliance hub UI
    res_page = client.get("/v57-compliance-hub")
    assert res_page.status_code == 200
    assert b"Registration Fee" in res_page.data or b"Decree 10/2022" in res_page.data

    # POST calculation
    res_calc = client.post("/api/v57/calculate", json={
        "mst": mock_tenant_db,
        "asset_description": "Test Car",
        "asset_type": "car",
        "asset_value": 2000000000.0,
        "province": "hanoi",
        "is_first_registration": True
    })
    assert res_calc.status_code == 200
    data_calc = json.loads(res_calc.data)
    assert data_calc["status"] == "success"
    assert data_calc["results"]["rate_pct"] == 12.0
    assert data_calc["results"]["effective_fee"] == 240000000.0

    # GET baseline compliance data
    res_data = client.get(f"/api/v57/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "real_estate_apt" in data
    assert "car_hanoi" in data
    assert "diplomatic_exempt" in data
    assert "motorbike_large" in data
    assert len(data["history"]) > 0
