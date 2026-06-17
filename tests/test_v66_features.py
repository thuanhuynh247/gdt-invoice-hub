"""Pytest verification suite for v66 GHG Emissions & Carbon Credits compliance.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v66_service import V66ComplianceService


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
    mst = "0102030466"
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


def test_ghg_emissions_energy(mock_tenant_db):
    """Energy sector emissions: CO2 (1), CH4 (28), N2O (265). Rate: 150k VND/tCO2e. Total >= 3000 to be taxable."""
    service = V66ComplianceService()
    res = service.calculate_ghg(
        mock_tenant_db, "Nhiệt điện Phả Lại", "energy", co2_tonnes=3000.0, ch4_tonnes=20.0, n2o_tonnes=10.0
    )
    # CO2e = 3000*1 + 20*28 + 10*265 = 3000 + 560 + 2650 = 6210 tCO2e
    assert res["total_co2e"] == 6210.0
    # Fee = 6210 * 150,000 = 931,500,000 VND
    assert res["fee_amount"] == 931500000.0
    assert res["is_exempt"] is False


def test_ghg_emissions_offset(mock_tenant_db):
    """Offset: carbon credits offset up to 10% cap. Total >= 3000 to be taxable."""
    service = V66ComplianceService()
    res = service.calculate_ghg(
        mock_tenant_db, "Nhiệt điện Phả Lại", "energy", co2_tonnes=4000.0, ch4_tonnes=0.0, n2o_tonnes=0.0,
        carbon_credits_offset=1000.0 # 1000 tCO2e offset, but cap is 10% of 4000 = 400 tCO2e
    )
    assert res["total_co2e"] == 4000.0
    assert res["taxable_co2e"] == 3600.0
    # Fee = 3600 * 150,000 = 540,000,000 VND
    assert res["fee_amount"] == 540000000.0


def test_ghg_small_emitter_exemption(mock_tenant_db):
    """Small emitter exemption: total CO2e < 3,000 tCO2e."""
    service = V66ComplianceService()
    res = service.calculate_ghg(
        mock_tenant_db, "Cơ sở dệt may", "energy", co2_tonnes=2900.0, ch4_tonnes=0.0, n2o_tonnes=0.0,
        exemption_category="small_emitter"
    )
    assert res["is_exempt"] is True
    assert res["fee_amount"] == 0.0


def test_ghg_history(mock_tenant_db):
    service = V66ComplianceService()
    service.calculate_ghg(mock_tenant_db, "Nhiệt điện Phả Lại", "energy", co2_tonnes=100.0, ch4_tonnes=0.0, n2o_tonnes=0.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["emission_description"] == "Nhiệt điện Phả Lại"


def test_api_routes_v66(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v66-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v66/calculate", json={
        "mst": mock_tenant_db,
        "emission_description": "API Test GHG",
        "facility_category": "energy",
        "co2_tonnes": 3500.0,
        "ch4_tonnes": 0.0,
        "n2o_tonnes": 0.0,
        "carbon_credits_offset": 20.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # CO2e = 3500, offset = 20 (within 10% cap). Net CO2e = 3480. Fee = 3480 * 150k = 522,000,000 VND
    assert data["results"]["fee_amount"] == 522000000.0

    res_data = client.get(f"/api/v66/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "standard_emissions" in d
    assert "offset_emissions" in d
    assert "small_exempt" in d
