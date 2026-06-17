"""Pytest verification suite for v54 Natural Resources Tax (NRT) Law 45/2009/QH12.

Verifies correct NRT rates for minerals, water, timber, and marine products, agricultural exemptions,
hydropower threshold checks, self-consumed resource rate adjustments, dashboard view rendering,
and REST JSON API endpoints using pytest.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v54_service import V54ComplianceService


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
    mst = "0102030493"
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


def test_mineral_nrt(mock_tenant_db):
    """Test NRT calculation for metallic ores and non-metallic minerals, and internal consumption adjustment (US-660, US-661)."""
    mst = mock_tenant_db
    service = V54ComplianceService()

    # Iron Ore: Metallic - 12%
    res = service.calculate_mineral_nrt(mst, "Iron Ore", "metallic", 1000.0, 500000.0, False)
    assert res["standard_rate"] == 0.12
    assert res["nrt_rate"] == 0.12
    assert res["nrt_amount"] == 1000.0 * 500000.0 * 0.12
    assert res["is_self_consumed"] == False

    # Copper: Metallic - 13%
    res = service.calculate_mineral_nrt(mst, "Copper", "metallic", 100.0, 1000000.0, False)
    assert res["standard_rate"] == 0.13
    assert res["nrt_rate"] == 0.13

    # Gold: Metallic - 15%
    res = service.calculate_mineral_nrt(mst, "Gold dust", "metallic", 10.0, 20000000.0, False)
    assert res["standard_rate"] == 0.15

    # Tin: Metallic - 20%
    res = service.calculate_mineral_nrt(mst, "Tin concentrate", "metallic", 50.0, 400000.0, False)
    assert res["standard_rate"] == 0.20

    # Granite: Non-metallic - 8%
    res = service.calculate_mineral_nrt(mst, "Granite slabs", "non-metallic", 100.0, 2000000.0, False)
    assert res["standard_rate"] == 0.08
    assert res["nrt_rate"] == 0.08

    # Sand: Non-metallic - 7%
    res = service.calculate_mineral_nrt(mst, "River Sand", "non-metallic", 500.0, 150000.0, False)
    assert res["standard_rate"] == 0.07

    # Marble: Non-metallic - 9%
    res = service.calculate_mineral_nrt(mst, "White Marble", "non-metallic", 200.0, 3000000.0, False)
    assert res["standard_rate"] == 0.09

    # Limestone: Non-metallic - 5%
    res = service.calculate_mineral_nrt(mst, "Limestone", "non-metallic", 1000.0, 100000.0, False)
    assert res["standard_rate"] == 0.05

    # Self-consumed Iron Ore: 30% reduction (70% effective rate)
    res_self = service.calculate_mineral_nrt(mst, "Iron Ore", "metallic", 1000.0, 500000.0, True)
    assert res_self["standard_rate"] == 0.12
    assert res_self["nrt_rate"] == pytest.approx(0.12 * 0.70)
    assert res_self["nrt_amount"] == pytest.approx(1000.0 * 500000.0 * 0.12 * 0.70)
    assert res_self["is_self_consumed"] == True


def test_water_nrt(mock_tenant_db):
    """Test water resource NRT with agricultural and small-scale hydropower exemptions (US-660, US-661)."""
    mst = mock_tenant_db
    service = V54ComplianceService()

    # Groundwater (non-exempt) - 4% default
    res = service.calculate_water_nrt(mst, "groundwater well", "industrial", 5000.0, 6000.0, 0.0)
    assert res["nrt_rate"] == 0.04
    assert res["nrt_amount"] == 5000.0 * 6000.0 * 0.04
    assert res["is_exempt"] == False

    # Surface water (non-exempt) - 2% default
    res = service.calculate_water_nrt(mst, "Red River surface water", "industrial", 10000.0, 3000.0, 0.0)
    assert res["nrt_rate"] == 0.02
    assert res["nrt_amount"] == 10000.0 * 3000.0 * 0.02
    assert res["is_exempt"] == False

    # Agricultural water exemption (Surface water, should be 100% exempt)
    res_agri = service.calculate_water_nrt(mst, "River Water", "agriculture", 20000.0, 2000.0, 0.0)
    assert res_agri["nrt_amount"] == 0.0
    assert res_agri["is_exempt"] == True
    assert "Agricultural" in res_agri["exemption_reason"]

    # Hydropower exemption: <= 2.0 MW capacity (should be 100% exempt)
    res_hydro_exempt = service.calculate_water_nrt(mst, "River Water", "hydropower", 50000.0, 500.0, 1.8)
    assert res_hydro_exempt["nrt_amount"] == 0.0
    assert res_hydro_exempt["is_exempt"] == True
    assert "Small-Scale Hydropower" in res_hydro_exempt["exemption_reason"]

    # Hydropower non-exemption: > 2.0 MW capacity
    res_hydro_taxed = service.calculate_water_nrt(mst, "River Water", "hydropower", 50000.0, 500.0, 2.5)
    assert res_hydro_taxed["nrt_amount"] == 50000.0 * 500.0 * 0.02
    assert res_hydro_taxed["is_exempt"] == False


def test_timber_nrt(mock_tenant_db):
    """Test timber NRT for natural forest vs. plantation timber (US-660)."""
    mst = mock_tenant_db
    service = V54ComplianceService()

    # Natural forest timber - 25% default
    res = service.calculate_timber_nrt(mst, "Ironwood", "natural forest", 50.0, 10000000.0)
    assert res["nrt_rate"] == 0.25
    assert res["nrt_amount"] == 50.0 * 10000000.0 * 0.25

    # Plantation timber - 3% default
    res = service.calculate_timber_nrt(mst, "Acacia logs", "plantation", 200.0, 1500000.0)
    assert res["nrt_rate"] == 0.03
    assert res["nrt_amount"] == 200.0 * 1500000.0 * 0.03


def test_marine_nrt(mock_tenant_db):
    """Test marine NRT for aquatic products vs. pearls/coral (US-660)."""
    mst = mock_tenant_db
    service = V54ComplianceService()

    # Aquatic products - 2% default
    res = service.calculate_marine_nrt(mst, "Tuna", "aquatic", 1000.0, 150000.0)
    assert res["nrt_rate"] == 0.02
    assert res["nrt_amount"] == 1000.0 * 150000.0 * 0.02

    # Pearls/Coral - 8% default
    res = service.calculate_marine_nrt(mst, "Black Pearls", "pearls/coral", 5.0, 50000000.0)
    assert res["nrt_rate"] == 0.08
    assert res["nrt_amount"] == 5.0 * 50000000.0 * 0.08


def test_api_routes_v54(mock_app, mock_tenant_db):
    """Test v54 HTTP API routes and view rendering (US-662)."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # Test GET Compliance Hub Page
    res_page = client.get("/v54-compliance-hub")
    assert res_page.status_code == 200
    assert b"Natural Resources Tax" in res_page.data or b"NRT" in res_page.data

    # Test GET Compliance Data API
    res_data = client.get(f"/api/v54/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "mineral_audit" in data
    assert "water_audit" in data
    assert "timber_audit" in data
    assert "marine_audit" in data
    assert "debate" in data

    # Test POST Mineral Calculate API
    res_min = client.post("/api/v54/mineral/calculate", json={
        "mst": mock_tenant_db,
        "mineral_name": "Gold Ore",
        "mineral_category": "metallic",
        "quantity": 100.0,
        "unit_price": 2000000.0,
        "is_self_consumed": True
    })
    assert res_min.status_code == 200
    min_data = json.loads(res_min.data)
    assert min_data["status"] == "success"
    assert min_data["results"]["standard_rate"] == 0.15
    assert min_data["results"]["nrt_rate"] == pytest.approx(0.15 * 0.70)

    # Test POST Water Calculate API
    res_wat = client.post("/api/v54/water/calculate", json={
        "mst": mock_tenant_db,
        "water_source": "Groundwater",
        "usage_purpose": "industrial",
        "volume_m3": 2000.0,
        "unit_price": 8000.0
    })
    assert res_wat.status_code == 200
    wat_data = json.loads(res_wat.data)
    assert wat_data["status"] == "success"
    assert wat_data["results"]["nrt_rate"] == 0.04

    # Test POST Timber Calculate API
    res_tim = client.post("/api/v54/timber/calculate", json={
        "mst": mock_tenant_db,
        "timber_name": "Teak Wood",
        "timber_source": "plantation",
        "volume_m3": 50.0,
        "unit_price": 5000000.0
    })
    assert res_tim.status_code == 200
    tim_data = json.loads(res_tim.data)
    assert tim_data["status"] == "success"
    assert tim_data["results"]["nrt_rate"] == 0.03

    # Test POST Marine Calculate API
    res_mar = client.post("/api/v54/marine/calculate", json={
        "mst": mock_tenant_db,
        "product_name": "Pink Coral",
        "product_category": "pearls/coral",
        "quantity_kg": 10.0,
        "unit_price": 15000000.0
    })
    assert res_mar.status_code == 200
    mar_data = json.loads(res_mar.data)
    assert mar_data["status"] == "success"
    assert mar_data["results"]["nrt_rate"] == 0.08
