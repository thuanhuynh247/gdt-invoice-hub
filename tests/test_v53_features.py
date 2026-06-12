"""Pytest verification suite for v53 Environmental Protection (EP) Tax Law 57/2010/QH12.

Tests fuel EP tax rates, coal classification-based rates, plastic bag biodegradable
exemptions, HCFC chemical taxation, transit/re-export exemptions, electricity-generation
coal exemptions, API routing, and view rendering.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v53_service import V53ComplianceService


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
    mst = "0102030492"
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


def test_fuel_ep_tax(mock_tenant_db):
    """Test fuel EP tax rates for petrol, diesel, and kerosene."""
    mst = mock_tenant_db
    service = V53ComplianceService()

    # Case 1: Petrol — 2,000 VND/litre
    res1 = service.calculate_fuel_ep_tax(mst, "petrol", 1000.0, 25000.0, False)
    assert res1["ep_tax_rate"] == 2000.0
    assert res1["ep_tax_amount"] == 2000000.0
    assert res1["is_exempt"] == False

    # Case 2: Diesel — 1,000 VND/litre
    res2 = service.calculate_fuel_ep_tax(mst, "diesel", 500.0, 20000.0, False)
    assert res2["ep_tax_rate"] == 1000.0
    assert res2["ep_tax_amount"] == 500000.0

    # Case 3: Kerosene — 600 VND/litre
    res3 = service.calculate_fuel_ep_tax(mst, "kerosene", 200.0, 18000.0, False)
    assert res3["ep_tax_rate"] == 600.0
    assert res3["ep_tax_amount"] == 120000.0

    # Case 4: Transit/Re-export — Fully exempt
    res4 = service.calculate_fuel_ep_tax(mst, "petrol", 1000.0, 25000.0, True)
    assert res4["ep_tax_amount"] == 0.0
    assert res4["is_exempt"] == True
    assert "Transit" in res4["exemption_reason"]


def test_coal_ep_tax(mock_tenant_db):
    """Test coal EP tax classification rates and electricity/export exemptions."""
    mst = mock_tenant_db
    service = V53ComplianceService()

    # Case 1: Anthracite — 30,000 VND/tonne
    res1 = service.calculate_coal_ep_tax(mst, "anthracite", 100.0, 3000000.0, "other")
    assert res1["ep_tax_rate"] == 30000.0
    assert res1["ep_tax_amount"] == 3000000.0
    assert res1["is_exempt"] == False

    # Case 2: Lignite — 20,000 VND/tonne
    res2 = service.calculate_coal_ep_tax(mst, "lignite", 100.0, 2000000.0, "other")
    assert res2["ep_tax_rate"] == 20000.0
    assert res2["ep_tax_amount"] == 2000000.0

    # Case 3: Other coal — 15,000 VND/tonne
    res3 = service.calculate_coal_ep_tax(mst, "bituminous coal", 100.0, 2500000.0, "other")
    assert res3["ep_tax_rate"] == 15000.0
    assert res3["ep_tax_amount"] == 1500000.0

    # Case 4: Coal for electricity generation — Fully exempt
    res4 = service.calculate_coal_ep_tax(mst, "anthracite", 100.0, 3000000.0, "electricity_generation")
    assert res4["ep_tax_amount"] == 0.0
    assert res4["is_exempt"] == True
    assert "Electricity" in res4["exemption_reason"]

    # Case 5: Coal for export — Fully exempt
    res5 = service.calculate_coal_ep_tax(mst, "lignite", 50.0, 1500000.0, "export")
    assert res5["ep_tax_amount"] == 0.0
    assert res5["is_exempt"] == True
    assert "Export" in res5["exemption_reason"]


def test_plastic_bag_ep_tax(mock_tenant_db):
    """Test plastic bag EP tax and biodegradable exemption."""
    mst = mock_tenant_db
    service = V53ComplianceService()

    # Case 1: Non-biodegradable bag — 50,000 VND/kg
    res1 = service.calculate_plastic_bag_ep_tax(mst, "Standard Bag", 10.0, 200000.0, False)
    assert res1["ep_tax_rate"] == 50000.0
    assert res1["ep_tax_amount"] == 500000.0

    # Case 2: Biodegradable bag — 100% exempt
    res2 = service.calculate_plastic_bag_ep_tax(mst, "Eco Bag", 10.0, 200000.0, True)
    assert res2["ep_tax_amount"] == 0.0
    assert res2["is_certified_biodegradable"] == True
    assert "Exempt" in res2["notes"]


def test_chemical_ep_tax(mock_tenant_db):
    """Test HCFC chemical EP tax and non-HCFC classification."""
    mst = mock_tenant_db
    service = V53ComplianceService()

    # Case 1: HCFC chemical — 5,000 VND/kg
    res1 = service.calculate_chemical_ep_tax(mst, "HCFC-22", 50.0, 5000000.0)
    assert res1["ep_tax_rate"] == 5000.0
    assert res1["ep_tax_amount"] == 250000.0
    assert "HCFC" in res1["notes"]

    # Case 2: Non-HCFC chemical — 0 VND/kg
    res2 = service.calculate_chemical_ep_tax(mst, "Sodium Chloride", 100.0, 1000000.0)
    assert res2["ep_tax_rate"] == 0.0
    assert res2["ep_tax_amount"] == 0.0
    assert "not classified" in res2["notes"]


def test_api_routes_v53(mock_app, mock_tenant_db):
    """Test v53 HTTP API routes and view rendering."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # Test GET Dashboard Page
    res_page = client.get("/v53-compliance-hub")
    assert res_page.status_code == 200
    assert b"Environmental Protection" in res_page.data or b"EP Tax" in res_page.data

    # Test GET Compliance Data API
    res_data = client.get(f"/api/v53/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "fuel_audit" in data
    assert "coal_audit" in data
    assert "bag_audit" in data
    assert "chemical_audit" in data
    assert "debate" in data

    # Test POST Fuel Calculate API
    res_fuel = client.post("/api/v53/fuel/calculate", json={
        "mst": mock_tenant_db,
        "fuel_type": "petrol",
        "quantity_litres": 500.0,
        "price_before_tax": 25000.0,
        "is_transit_or_reexport": False
    })
    assert res_fuel.status_code == 200
    res_fuel_data = json.loads(res_fuel.data)
    assert res_fuel_data["status"] == "success"
    assert res_fuel_data["results"]["ep_tax_rate"] == 2000.0
    assert res_fuel_data["results"]["ep_tax_amount"] == 1000000.0

    # Test POST Coal Calculate API
    res_coal = client.post("/api/v53/coal/calculate", json={
        "mst": mock_tenant_db,
        "coal_type": "anthracite",
        "quantity_tonnes": 100.0,
        "price_before_tax": 3000000.0,
        "usage": "other"
    })
    assert res_coal.status_code == 200
    res_coal_data = json.loads(res_coal.data)
    assert res_coal_data["status"] == "success"
    assert res_coal_data["results"]["ep_tax_rate"] == 30000.0
    assert res_coal_data["results"]["ep_tax_amount"] == 3000000.0

    # Test POST Bag Calculate API
    res_bag = client.post("/api/v53/bag/calculate", json={
        "mst": mock_tenant_db,
        "bag_name": "Test Bag",
        "weight_kg": 20.0,
        "price_before_tax": 100000.0,
        "is_certified_biodegradable": False
    })
    assert res_bag.status_code == 200
    res_bag_data = json.loads(res_bag.data)
    assert res_bag_data["status"] == "success"
    assert res_bag_data["results"]["ep_tax_amount"] == 1000000.0

    # Test POST Chemical Calculate API
    res_chem = client.post("/api/v53/chemical/calculate", json={
        "mst": mock_tenant_db,
        "chemical_name": "HCFC-141b",
        "weight_kg": 25.0,
        "price_before_tax": 2500000.0
    })
    assert res_chem.status_code == 200
    res_chem_data = json.loads(res_chem.data)
    assert res_chem_data["status"] == "success"
    assert res_chem_data["results"]["ep_tax_rate"] == 5000.0
    assert res_chem_data["results"]["ep_tax_amount"] == 125000.0
