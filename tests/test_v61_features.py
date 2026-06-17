"""Pytest verification suite for v61 Environment Protection Fee for Wastewater (EPFW).

Verifies wastewater fee calculations under Decree 53/2020/NĐ-CP for domestic and
industrial wastewater, heavy metals variable fees, exemptions, and REST APIs.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v61_service import V61ComplianceService


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
    mst = "0102030499"
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


def test_epfw_domestic_standard(mock_tenant_db):
    """Domestic wastewater fee: 10% of clean water bill before VAT."""
    service = V61ComplianceService()
    res = service.calculate_epfw(
        mock_tenant_db, "Home", "domestic", water_volume_m3=150.0, clean_water_price_vnd=12000.0, water_source="central_water"
    )
    assert res["base_fee_vnd"] == 0.0
    # Clean water bill = 150 * 12,000 = 1,800,000 VND. Fee = 1,800,000 * 10% = 180,000 VND.
    assert res["variable_fee_vnd"] == pytest.approx(180000.0, rel=1e-3)
    assert res["total_fee_vnd"] == pytest.approx(180000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(180000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epfw_industrial_heavy_metals(mock_tenant_db):
    """Industrial wastewater: 1,500,000 VND fixed base + variable chemical loads."""
    service = V61ComplianceService()
    res = service.calculate_epfw(
        mock_tenant_db,
        "Dyeing Factory",
        "industrial",
        water_volume_m3=500.0,
        pollutant_cod_kg=120.0,  # 120 * 2,000 = 240,000
        pollutant_tss_kg=80.0,   # 80 * 2,400 = 192,000
        pollutant_pb_kg=0.5,     # 0.5 * 1,000,000 = 500,000
        water_source="central_water"
    )
    assert res["base_fee_vnd"] == 1500000.0
    # Variable = 240,000 + 192,000 + 500,000 = 932,000 VND.
    assert res["variable_fee_vnd"] == pytest.approx(932000.0, rel=1e-3)
    assert res["total_fee_vnd"] == pytest.approx(1500000.0 + 932000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(2432000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epfw_cooling_recycling_exempt(mock_tenant_db):
    """Cooling water recycling system is 100% exempt."""
    service = V61ComplianceService()
    res = service.calculate_epfw(
        mock_tenant_db, "Cooling Water", "industrial", water_volume_m3=1000.0, water_source="cooling_recycling"
    )
    assert res["is_exempt"] is True
    assert res["effective_fee_vnd"] == 0.0


def test_epfw_natural_runoff_exempt(mock_tenant_db):
    """Natural rainwater/runoff is 100% exempt."""
    service = V61ComplianceService()
    res = service.calculate_epfw(
        mock_tenant_db, "Rainwater Drainage", "domestic", water_volume_m3=2000.0, water_source="natural_runoff"
    )
    assert res["is_exempt"] is True
    assert res["effective_fee_vnd"] == 0.0


def test_epfw_history(mock_tenant_db):
    service = V61ComplianceService()
    service.calculate_epfw(mock_tenant_db, "Audit Discharge", "industrial", 10.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["water_description"] == "Audit Discharge"


def test_api_routes_v61(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v61-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v61/calculate", json={
        "mst": mock_tenant_db,
        "water_description": "API Discharge",
        "wastewater_type": "industrial",
        "water_volume_m3": 100.0,
        "water_source": "cooling_recycling"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    assert data["results"]["effective_fee_vnd"] == 0.0
    assert data["results"]["is_exempt"] is True

    res_data = client.get(f"/api/v61/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "domestic_standard" in d
    assert "industrial_heavy_metals" in d
    assert "cooling_exempt" in d
    assert "runoff_exempt" in d
