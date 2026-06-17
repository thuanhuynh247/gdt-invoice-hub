"""Pytest verification suite for v52 Special Consumption Tax (SCT) Law No. 66/2025/QH15.

Tests sugary beverages tax roadmaps, air conditioner capacity thresholds,
inland-to-nontariff area sales, promotional price adjustments, API routing, and views.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v52_service import V52ComplianceService


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
    mst = "0102030491"
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


def test_sugary_beverage_sct(mock_tenant_db):
    """Test sugary beverage classifications and roadmap rates (2026-2028)."""
    mst = mock_tenant_db
    service = V52ComplianceService()

    # Case 1: Excluded category (milk) -> 0% SCT rate
    res1 = service.calculate_sugary_beverage_sct(mst, "Premium Milk", 8.0, "milk", 2028, 15000.0)
    assert res1["sct_rate"] == 0.0
    assert res1["sct_amount"] == 0.0
    assert "Exempt" in res1["notes"]

    # Case 2: Sugar content <= 5g/100ml -> 0% SCT rate
    res2 = service.calculate_sugary_beverage_sct(mst, "Diet Soda", 4.5, "soft drink", 2028, 12000.0)
    assert res2["sct_rate"] == 0.0
    assert res2["sct_amount"] == 0.0
    assert "Compliant" in res2["notes"]

    # Case 3: Sugar content > 5g/100ml in Year 2026 -> 0% SCT rate
    res3 = service.calculate_sugary_beverage_sct(mst, "Sweet Tea", 7.5, "soft drink", 2026, 20000.0)
    assert res3["sct_rate"] == 0.0
    assert res3["sct_amount"] == 0.0

    # Case 4: Sugar content > 5g/100ml in Year 2027 -> 8% SCT rate
    res4 = service.calculate_sugary_beverage_sct(mst, "Sweet Tea", 7.5, "soft drink", 2027, 20000.0)
    assert res4["sct_rate"] == 0.08
    assert res4["sct_amount"] == 1600.0

    # Case 5: Sugar content > 5g/100ml in Year 2028 -> 10% SCT rate
    res5 = service.calculate_sugary_beverage_sct(mst, "Sweet Tea", 7.5, "soft drink", 2028, 20000.0)
    assert res5["sct_rate"] == 0.10
    assert res5["sct_amount"] == 2000.0


def test_air_conditioner_sct(mock_tenant_db):
    """Test air conditioner capacity-based SCT limits."""
    mst = mock_tenant_db
    service = V52ComplianceService()

    # Case 1: Capacity <= 24,000 BTU -> Exempt (0% SCT)
    res1 = service.calculate_air_conditioner_sct(mst, "AC Unit Small", 24000.0, 10000000.0)
    assert res1["sct_rate"] == 0.0
    assert res1["sct_amount"] == 0.0

    # Case 2: Capacity > 90,000 BTU -> Exempt (0% SCT)
    res2 = service.calculate_air_conditioner_sct(mst, "AC Unit Large", 120000.0, 45000000.0)
    assert res2["sct_rate"] == 0.0
    assert res2["sct_amount"] == 0.0

    # Case 3: Capacity in taxable range (e.g. 30,000 BTU) -> Taxable (10% SCT)
    res3 = service.calculate_air_conditioner_sct(mst, "AC Unit Medium", 30000.0, 15000000.0)
    assert res3["sct_rate"] == 0.10
    assert res3["sct_amount"] == 1500000.0


def test_nontariff_sct(mock_tenant_db):
    """Test inland sales into non-tariff area rules."""
    mst = mock_tenant_db
    service = V52ComplianceService()

    # Case 1: Standard item sold to non-tariff zone -> Taxable
    res1 = service.calculate_nontariff_sct(mst, "Steel Beams", "Linh Trung EPZ", False, 100000000.0)
    assert res1["sct_rate"] == 0.10
    assert res1["sct_amount"] == 10000000.0

    # Case 2: Passenger car with < 24 seats sold to non-tariff zone -> Exempt under this rule
    res2 = service.calculate_nontariff_sct(mst, "Sedan Car", "Linh Trung EPZ", True, 800000000.0)
    assert res2["sct_rate"] == 0.0
    assert res2["sct_amount"] == 0.0


def test_promotion_sct(mock_tenant_db):
    """Test promotional equivalent pricing adjustment for SCT."""
    mst = mock_tenant_db
    service = V52ComplianceService()

    # Case: Promo price is 0, equivalent market price is 15,000, qty 1,000, sct_rate 10%
    # Total Base = 15,000 * 1,000 = 15,000,000. SCT = 1,500,000.
    res = service.calculate_promotion_sct(mst, "Beer Sample", 0.0, 15000.0, 1000, 0.10)
    assert res["sct_rate"] == 0.10
    assert res["sct_amount"] == 1500000.0
    assert "Tax Base Adjusted" in res["notes"]


def test_api_routes_v52(mock_app, mock_tenant_db):
    """Test v52 HTTP API routes and view rendering."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # Test GET Dashboard Page
    res_page = client.get("/v52-compliance-hub")
    assert res_page.status_code == 200
    assert b"SCT Law 66" in res_page.data or b"Special Consumption" in res_page.data

    # Test GET Compliance Data API
    res_data = client.get(f"/api/v52/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "beverage_audit" in data
    assert "ac_audit" in data
    assert "nontariff_audit" in data
    assert "promo_audit" in data
    assert "debate" in data

    # Test POST Beverage Calculate API
    res_bev = client.post("/api/v52/beverage/calculate", json={
        "mst": mock_tenant_db,
        "drink_name": "Soda Extreme",
        "sugar_content": 9.2,
        "category": "soft drink",
        "year": 2028,
        "price_before_tax": 25000.0
    })
    assert res_bev.status_code == 200
    res_bev_data = json.loads(res_bev.data)
    assert res_bev_data["status"] == "success"
    assert res_bev_data["results"]["sct_rate"] == 0.10
    assert res_bev_data["results"]["sct_amount"] == 2500.0

    # Test POST AC Calculate API
    res_ac = client.post("/api/v52/ac/calculate", json={
        "mst": mock_tenant_db,
        "model_name": "CoolSystem 50k",
        "capacity_btu": 50000.0,
        "price_before_tax": 20000000.0
    })
    assert res_ac.status_code == 200
    res_ac_data = json.loads(res_ac.data)
    assert res_ac_data["status"] == "success"
    assert res_ac_data["results"]["sct_rate"] == 0.10
    assert res_ac_data["results"]["sct_amount"] == 2000000.0

    # Test POST Non-Tariff Calculate API
    res_nt = client.post("/api/v52/nontariff/calculate", json={
        "mst": mock_tenant_db,
        "item_name": "Export Wood Panel",
        "destination": "Saigon EPZ",
        "is_car_under_24_seats": False,
        "price_before_tax": 30000000.0
    })
    assert res_nt.status_code == 200
    res_nt_data = json.loads(res_nt.data)
    assert res_nt_data["status"] == "success"
    assert res_nt_data["results"]["sct_rate"] == 0.10

    # Test POST Promotion Calculate API
    res_promo = client.post("/api/v52/promotion/calculate", json={
        "mst": mock_tenant_db,
        "item_name": "Soda Gift Pack",
        "promo_price": 0.0,
        "equivalent_price": 10000.0,
        "quantity": 500,
        "sct_rate": 10.0
    })
    assert res_promo.status_code == 200
    res_promo_data = json.loads(res_promo.data)
    assert res_promo_data["status"] == "success"
    assert res_promo_data["results"]["sct_amount"] == 500000.0
