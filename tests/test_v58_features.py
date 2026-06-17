"""Pytest verification suite for v58 Natural Resources Tax (NRT) Law 45/2009/QH12.

Verifies correct NRT calculations for metallic minerals, non-metallic minerals,
crude oil (sliding scale), natural gas, coal, water, timber, marine products,
exemptions for agricultural water, hydroelectric water, defense resources,
and REST JSON API endpoints.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v58_service import V58ComplianceService


@pytest.fixture
def mock_app():
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
    mst = "0102030498"
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


def test_nrt_iron_ore(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Iron Mine A", "metallic", "iron_ore", 50000000000.0)
    assert res["rate_pct"] == 12.0
    assert res["nrt_amount"] == 6000000000.0
    assert res["is_exempt"] is False


def test_nrt_gold_ore(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Gold Mine B", "metallic", "gold_ore", 100000000000.0)
    assert res["rate_pct"] == 15.0
    assert res["nrt_amount"] == 15000000000.0


def test_nrt_sand(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Sand Quarry", "non_metallic", "sand", 10000000000.0)
    assert res["rate_pct"] == 7.0
    assert res["nrt_amount"] == pytest.approx(700000000.0)


def test_nrt_crude_oil_low_output(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Oil Field A", "crude_oil", "", 500000000000.0, daily_output=15000)
    assert res["rate_pct"] == 6.0
    assert res["nrt_amount"] == 30000000000.0


def test_nrt_crude_oil_high_output(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Oil Field B", "crude_oil", "", 500000000000.0, daily_output=25000)
    assert res["rate_pct"] == 10.0
    assert res["nrt_amount"] == 50000000000.0


def test_nrt_natural_gas(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Gas Well", "natural_gas", "", 200000000000.0)
    assert res["rate_pct"] == 2.0
    assert res["nrt_amount"] == 4000000000.0


def test_nrt_coal_open_pit(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Coal Open Pit", "coal", "open_pit", 80000000000.0)
    assert res["rate_pct"] == 7.0
    assert res["nrt_amount"] == pytest.approx(5600000000.0)


def test_nrt_coal_underground(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Coal Underground", "coal", "underground", 80000000000.0)
    assert res["rate_pct"] == 5.0
    assert res["nrt_amount"] == 4000000000.0


def test_nrt_timber_hardwood(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Hardwood Timber", "timber", "hardwood", 20000000000.0)
    assert res["rate_pct"] == 25.0
    assert res["nrt_amount"] == 5000000000.0


def test_nrt_marine(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Natural Catch", "marine", "", 5000000000.0)
    assert res["rate_pct"] == 2.0
    assert res["nrt_amount"] == 100000000.0


def test_nrt_agri_water_exemption(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Rice Irrigation Water", "water", "", 1000000000.0, is_agri_water=True)
    assert res["is_exempt"] is True
    assert res["effective_amount"] == 0.0
    assert "agriculture" in res["exemption_reason"].lower()


def test_nrt_hydro_water_exemption(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Hydroelectric Water", "water", "", 2000000000.0, is_hydro_water=True)
    assert res["is_exempt"] is True
    assert res["effective_amount"] == 0.0
    assert "hydroelectric" in res["exemption_reason"].lower()


def test_nrt_defense_exemption(mock_tenant_db):
    service = V58ComplianceService()
    res = service.calculate_nrt(mock_tenant_db, "Defense Iron", "metallic", "iron_ore", 30000000000.0, is_defense=True)
    assert res["is_exempt"] is True
    assert res["effective_amount"] == 0.0
    assert "defense" in res["exemption_reason"].lower()


def test_nrt_history(mock_tenant_db):
    service = V58ComplianceService()
    service.calculate_nrt(mock_tenant_db, "Test Resource", "coal", "", 10000000000.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["resource_description"] == "Test Resource"


def test_api_routes_v58(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v58-compliance-hub")
    assert res_page.status_code == 200
    assert b"Natural Resources" in res_page.data or b"Law 45/2009" in res_page.data

    res_calc = client.post("/api/v58/calculate", json={
        "mst": mock_tenant_db,
        "resource_description": "Test Gold",
        "resource_type": "metallic",
        "resource_subtype": "gold_ore",
        "extraction_value": 100000000000.0
    })
    assert res_calc.status_code == 200
    data_calc = json.loads(res_calc.data)
    assert data_calc["status"] == "success"
    assert data_calc["results"]["rate_pct"] == 15.0

    res_data = client.get(f"/api/v58/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "iron_ore" in data
    assert "crude_oil_high" in data
    assert "agri_water_exempt" in data
    assert len(data["history"]) > 0
