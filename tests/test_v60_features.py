"""Pytest verification suite for v60 Agricultural Land Use Tax Law 1993.

Verifies ALUT calculations for annual/perennial crop land grades, rice-to-VND
conversion, producer-type exemptions, and REST API endpoints.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v60_service import V60ComplianceService


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


def test_alut_annual_grade1_household(mock_tenant_db):
    """Annual crop land grade 1 (550 kg/ha) for household is 100% exempt."""
    service = V60ComplianceService()
    res = service.calculate_alut(mock_tenant_db, "Rice Field", 1, "annual", area_ha=2.5, producer_type="household", rice_price_per_kg=8000.0)
    assert res["standard_rice_rate_kg"] == 550.0
    assert res["tax_amount_rice"] == 550.0 * 2.5
    assert res["tax_amount_vnd"] == 550.0 * 2.5 * 8000.0
    assert res["effective_amount_vnd"] == 0.0
    assert res["is_exempt"] is True


def test_alut_perennial_grade3_cooperative(mock_tenant_db):
    """Perennial crop land grade 3 (400 kg/ha) for cooperative is 100% exempt."""
    service = V60ComplianceService()
    res = service.calculate_alut(mock_tenant_db, "Tea Farm", 3, "perennial", area_ha=10.0, producer_type="cooperative", rice_price_per_kg=9000.0)
    assert res["standard_rice_rate_kg"] == 400.0
    assert res["tax_amount_rice"] == 400.0 * 10.0
    assert res["tax_amount_vnd"] == 400.0 * 10.0 * 9000.0
    assert res["effective_amount_vnd"] == 0.0
    assert res["is_exempt"] is True


def test_alut_state_rubber_reduced(mock_tenant_db):
    """State-owned agricultural enterprise gets 50% discount."""
    service = V60ComplianceService()
    res = service.calculate_alut(mock_tenant_db, "Rubber Farm", 1, "perennial", area_ha=100.0, producer_type="state_org", rice_price_per_kg=8000.0)
    assert res["standard_rice_rate_kg"] == 650.0
    assert res["tax_amount_vnd"] == 650.0 * 100.0 * 8000.0
    # 50% reduction
    assert res["effective_amount_vnd"] == (650.0 * 100.0 * 8000.0) * 0.50
    assert res["is_exempt"] is True
    assert "50%" in res["exemption_reason"]


def test_alut_general_company_taxable(mock_tenant_db):
    """General company gets no waiver (taxable)."""
    service = V60ComplianceService()
    res = service.calculate_alut(mock_tenant_db, "Commercial Orchard", 4, "annual", area_ha=20.0, producer_type="general_org", rice_price_per_kg=8000.0)
    assert res["standard_rice_rate_kg"] == 280.0
    assert res["tax_amount_vnd"] == 280.0 * 20.0 * 8000.0
    assert res["effective_amount_vnd"] == res["tax_amount_vnd"]
    assert res["is_exempt"] is False


def test_alut_history(mock_tenant_db):
    service = V60ComplianceService()
    service.calculate_alut(mock_tenant_db, "History Land", 5, "annual", 1.0, "household")
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["land_description"] == "History Land"


def test_api_routes_v60(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v60-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v60/calculate", json={
        "mst": mock_tenant_db,
        "land_description": "API Land",
        "land_grade": 2,
        "crop_type": "annual",
        "area_ha": 4.5,
        "producer_type": "state_org",
        "rice_price_per_kg": 8000
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # Grade 2: 460 kg/ha * 4.5 ha * 8000 VND/kg * 0.50 (state_org reduction) = 8,280,000 VND
    assert data["results"]["effective_amount_vnd"] == 460 * 4.5 * 8000 * 0.5

    res_data = client.get(f"/api/v60/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "household_exempt" in d
    assert "coop_exempt" in d
    assert "state_enterprise_reduced" in d
    assert "general_company_taxable" in d
