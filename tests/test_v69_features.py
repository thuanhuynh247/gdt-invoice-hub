"""Pytest verification suite for v69 Oil Spill Response & Risk Fee compliance.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v69_service import V69ComplianceService


@pytest.fixture
def mock_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["BASE_DATA_DIR"] = os.path.dirname(__file__)
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
    mst = "0102030469"
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


def test_spill_refinery(mock_tenant_db):
    """Refinery: Base 50M. Capacity charge: 500 VND/m³."""
    service = V69ComplianceService()
    res = service.calculate_spill_fee(
        mock_tenant_db, "Dung Quất Refinery", "refinery_or_extraction", capacity_m3=100000.0, has_double_hull=False
    )
    # Base fee = 50,000,000
    # Capacity charge = 100,000 * 500 = 50,000,000
    # Total fee = 100,000,000
    assert res["base_fee"] == 50000000.0
    assert res["capacity_charge"] == 50000000.0
    assert res["final_fee"] == 100000000.0
    assert res["is_exempt"] is False


def test_spill_double_hull_discount(mock_tenant_db):
    """Transport Fleet with double hull: 30% discount."""
    service = V69ComplianceService()
    res = service.calculate_spill_fee(
        mock_tenant_db, "Petrolimex Fleet", "transport_fleet", capacity_m3=20000.0, has_double_hull=True
    )
    # Base fee = 20,000,000
    # Capacity charge = 20,000 * 500 = 10,000,000
    # Total = 30,000,000
    # Discount = 30% -> discount_applied = 9,000,000
    # final_fee = 30,000,000 - 9,000,000 = 21,000,000
    assert res["base_fee"] == 20000000.0
    assert res["capacity_charge"] == 10000000.0
    assert res["discount_applied"] == 9000000.0
    assert res["final_fee"] == 21000000.0


def test_spill_military_exemption(mock_tenant_db):
    """Military petroleum exemption."""
    service = V69ComplianceService()
    res = service.calculate_spill_fee(
        mock_tenant_db, "K52 Depot", "storage_terminal", capacity_m3=8000.0, exemption_category="military_petroleum"
    )
    assert res["is_exempt"] is True
    assert res["final_fee"] == 0.0


def test_spill_history(mock_tenant_db):
    service = V69ComplianceService()
    service.calculate_spill_fee(mock_tenant_db, "K52 Depot", "storage_terminal", capacity_m3=8000.0, exemption_category="military_petroleum")
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["facility_name"] == "K52 Depot"


def test_api_routes_v69(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v69-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v69/calculate", json={
        "mst": mock_tenant_db,
        "facility_name": "API Spill Terminal",
        "facility_type": "storage_terminal",
        "capacity_m3": 10000.0,
        "has_double_hull": False,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # Base: 30M. Capacity: 10,000 * 500 = 5M. Total = 35M VND
    assert data["results"]["final_fee"] == 35000000.0

    res_data = client.get(f"/api/v69/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "terminal_standard" in d
    assert "fleet_discount" in d
    assert "military_exempt" in d
