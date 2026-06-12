"""Pytest verification suite for v63 Environment Protection Fee for Mineral Extraction (EPFME).

Verifies mineral extraction fee calculations under Decree 27/2023/NĐ-CP, salvage reductions,
exemptions, and REST APIs.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v63_service import V63ComplianceService


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


def test_epfme_crude_oil_standard(mock_tenant_db):
    """Crude Oil standard rate: 100,000 VND / tonne."""
    service = V63ComplianceService()
    res = service.calculate_epfme(
        mock_tenant_db, "Mỏ Bạch Hổ", "crude_oil", volume=5000.0, is_salvage=False
    )
    assert res["base_rate"] == 100000.0
    assert res["applied_rate"] == 100000.0
    # 5,000 * 100,000 = 500,000,000 VND
    assert res["total_fee_vnd"] == pytest.approx(500000000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(500000000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epfme_salvage_reduction(mock_tenant_db):
    """Building Stone salvage rate: 60% of 7,500 = 4,500 VND/m³."""
    service = V63ComplianceService()
    res = service.calculate_epfme(
        mock_tenant_db, "Khai thác đá tận thu", "building_stone", volume=10000.0, is_salvage=True
    )
    assert res["base_rate"] == 7500.0
    assert res["applied_rate"] == 4500.0
    # 10,000 * 4,500 = 45,000,000 VND
    assert res["total_fee_vnd"] == pytest.approx(45000000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(45000000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epfme_exemptions(mock_tenant_db):
    """Exemptions under Decree 27/2023/NĐ-CP: household_building, security_military_disaster, environmental_reclamation."""
    service = V63ComplianceService()
    
    # Household construction
    res_house = service.calculate_epfme(
        mock_tenant_db, "Personal land clay", "brick_clay", volume=200.0, exemption_category="household_building"
    )
    assert res_house["is_exempt"] is True
    assert res_house["effective_fee_vnd"] == 0.0
    
    # Disaster relief
    res_disaster = service.calculate_epfme(
        mock_tenant_db, "Flood control rock", "building_stone", volume=15000.0, exemption_category="security_military_disaster"
    )
    assert res_disaster["is_exempt"] is True
    assert res_disaster["effective_fee_vnd"] == 0.0

    # Reclamation
    res_reclaim = service.calculate_epfme(
        mock_tenant_db, "Restoration backfill", "brick_clay", volume=8000.0, exemption_category="environmental_reclamation"
    )
    assert res_reclaim["is_exempt"] is True
    assert res_reclaim["effective_fee_vnd"] == 0.0


def test_epfme_history(mock_tenant_db):
    service = V63ComplianceService()
    service.calculate_epfme(mock_tenant_db, "Gas drilling", "natural_gas", 50000.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["mineral_description"] == "Gas drilling"


def test_api_routes_v63(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v63-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v63/calculate", json={
        "mst": mock_tenant_db,
        "mineral_description": "API coal extraction",
        "mineral_type": "associated_gas",
        "volume": 200000.0,
        "is_salvage": False,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # 200,000 * 35 = 7,000,000 VND
    assert data["results"]["effective_fee_vnd"] == 7000000.0

    res_data = client.get(f"/api/v63/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "crude_oil_standard" in d
    assert "stone_salvage" in d
    assert "household_exempt" in d
    assert "disaster_exempt" in d
