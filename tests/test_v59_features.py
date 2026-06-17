"""Pytest verification suite for v59 NALUT Law 48/2010/QH12.

Verifies Non-Agricultural Land Use Tax calculations for residential (tiered),
commercial, production, idle land surcharge, exemptions, and REST API endpoints.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v59_service import V59ComplianceService


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


def test_nalut_residential_within_quota(mock_tenant_db):
    """Residential land within quota: 0.03%."""
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "House Q1", "residential", 10000000000.0, land_area=200, quota_area=200)
    assert res["rate_pct"] == pytest.approx(0.03, abs=0.001)
    assert res["tax_amount"] == pytest.approx(3000000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_nalut_residential_exceed_quota(mock_tenant_db):
    """Residential land exceeding 3x quota: progressive tiers."""
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Villa", "residential", 20000000000.0, land_area=800, quota_area=200)
    # Tier1: 200/800 * 20B * 0.03% = 1,500,000
    # Tier2: (600-200=400)/800 * 20B * 0.07% = 7,000,000  (mid excess from 200 to 600=min(800,600))
    # Tier3: (800-600=200)/800 * 20B * 0.15% = 7,500,000
    assert res["tax_amount"] > 3000000.0  # Must be more than flat 0.03%
    assert res["is_exempt"] is False


def test_nalut_commercial(mock_tenant_db):
    """Commercial land: flat 0.03%."""
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Shop", "commercial", 5000000000.0)
    assert res["rate_pct"] == 0.03
    assert res["tax_amount"] == pytest.approx(1500000.0, rel=1e-3)


def test_nalut_production(mock_tenant_db):
    """Production land: flat 0.03%."""
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Factory", "production", 8000000000.0)
    assert res["rate_pct"] == 0.03
    assert res["tax_amount"] == pytest.approx(2400000.0, rel=1e-3)


def test_nalut_idle_land_surcharge(mock_tenant_db):
    """Idle land 5 years: 0.03% + 0.02%*5 = 0.13%."""
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Empty Lot", "idle", 10000000000.0, idle_years=5)
    assert res["rate_pct"] == pytest.approx(0.13, abs=0.001)
    assert res["tax_amount"] == pytest.approx(13000000.0, rel=1e-3)


def test_nalut_idle_land_cap(mock_tenant_db):
    """Idle land surcharge capped at 0.15%."""
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Very Old Empty Lot", "idle", 10000000000.0, idle_years=20)
    assert res["rate_pct"] == 0.15
    assert res["tax_amount"] == pytest.approx(15000000.0, rel=1e-3)


def test_nalut_public_welfare_exemption(mock_tenant_db):
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Hospital", "commercial", 50000000000.0, is_public_welfare=True)
    assert res["is_exempt"] is True
    assert res["effective_amount"] == 0.0
    assert "welfare" in res["exemption_reason"].lower()


def test_nalut_religious_exemption(mock_tenant_db):
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Pagoda Land", "residential", 30000000000.0, is_religious=True)
    assert res["is_exempt"] is True
    assert res["effective_amount"] == 0.0
    assert "religious" in res["exemption_reason"].lower()


def test_nalut_diplomatic_exemption(mock_tenant_db):
    service = V59ComplianceService()
    res = service.calculate_nalut(mock_tenant_db, "Embassy", "commercial", 100000000000.0, is_diplomatic=True)
    assert res["is_exempt"] is True
    assert res["effective_amount"] == 0.0
    assert "diplomatic" in res["exemption_reason"].lower()


def test_nalut_history(mock_tenant_db):
    service = V59ComplianceService()
    service.calculate_nalut(mock_tenant_db, "Test Plot", "commercial", 5000000000.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["land_description"] == "Test Plot"


def test_api_routes_v59(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v59-compliance-hub")
    assert res_page.status_code == 200
    assert b"Non-Agricultural" in res_page.data or b"NALUT" in res_page.data or b"Law 48/2010" in res_page.data

    res_calc = client.post("/api/v59/calculate", json={
        "mst": mock_tenant_db,
        "land_description": "Test Land",
        "land_type": "commercial",
        "land_value": 5000000000.0
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    assert data["results"]["rate_pct"] == 0.03

    res_data = client.get(f"/api/v59/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "residential_within" in d
    assert "idle_land" in d
    assert "religious_exempt" in d
