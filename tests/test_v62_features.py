"""Pytest verification suite for v62 Environment Protection Fee for Emissions (EPFE).

Verifies emissions fee calculations under Decree 153/2024/NĐ-CP, variable pollutant loads,
exemptions, and REST APIs.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v62_service import V62ComplianceService


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


def test_epfe_fixed_only_annual(mock_tenant_db):
    """If monitoring is not required, only the annual flat fixed fee of 3,000,000 VND applies."""
    service = V62ComplianceService()
    res = service.calculate_epfe(
        mock_tenant_db, "Small workshop", "general_industrial", period="annual", is_subject_to_monitoring=False
    )
    assert res["base_fee_vnd"] == 3000000.0
    assert res["variable_fee_vnd"] == 0.0
    assert res["total_fee_vnd"] == 3000000.0
    assert res["effective_fee_vnd"] == 3000000.0
    assert res["is_exempt"] is False


def test_epfe_fixed_only_quarterly(mock_tenant_db):
    """If monitoring is not required and period is quarterly, only 750,000 VND applies."""
    service = V62ComplianceService()
    res = service.calculate_epfe(
        mock_tenant_db, "Small workshop", "general_industrial", period="quarterly", is_subject_to_monitoring=False
    )
    assert res["base_fee_vnd"] == 750000.0
    assert res["variable_fee_vnd"] == 0.0
    assert res["total_fee_vnd"] == 750000.0
    assert res["effective_fee_vnd"] == 750000.0
    assert res["is_exempt"] is False


def test_epfe_standard_pollutant_loads(mock_tenant_db):
    """Test standard industrial plant subject to emissions monitoring and variable fees."""
    service = V62ComplianceService()
    res = service.calculate_epfe(
        mock_tenant_db,
        "Cement factory emissions",
        "cement",
        period="quarterly",
        is_subject_to_monitoring=True,
        pollutant_dust_kg=1200.0,  # 1200 * 0.8 = 960 VND
        pollutant_nox_kg=800.0,    # 800 * 0.8 = 640 VND
        pollutant_sox_kg=1500.0,   # 1500 * 0.7 = 1050 VND
        pollutant_co_kg=2000.0,    # 2000 * 0.5 = 1000 VND
    )
    assert res["base_fee_vnd"] == 750000.0
    # Variable = 960 + 640 + 1050 + 1000 = 3650 VND
    assert res["variable_fee_vnd"] == pytest.approx(3650.0, rel=1e-3)
    assert res["total_fee_vnd"] == pytest.approx(753650.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(753650.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epfe_exemptions(mock_tenant_db):
    """Test 100% exemptions for certified zero-emissions or out-of-scope operations."""
    service = V62ComplianceService()
    
    # Zero emissions
    res_zero = service.calculate_epfe(
        mock_tenant_db, "Solar Plant", "general_industrial", "annual", True, exemption_category="zero_emissions"
    )
    assert res_zero["is_exempt"] is True
    assert res_zero["effective_fee_vnd"] == 0.0
    
    # Out of scope
    res_out = service.calculate_epfe(
        mock_tenant_db, "Hộ cá thể", "general_industrial", "annual", True, exemption_category="out_of_scope"
    )
    assert res_out["is_exempt"] is True
    assert res_out["effective_fee_vnd"] == 0.0


def test_epfe_history(mock_tenant_db):
    service = V62ComplianceService()
    service.calculate_epfe(mock_tenant_db, "Audit Stack", "cement", "annual", False)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["emission_description"] == "Audit Stack"


def test_api_routes_v62(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v62-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v62/calculate", json={
        "mst": mock_tenant_db,
        "emission_description": "API stack",
        "facility_type": "iron_steel",
        "period": "annual",
        "is_subject_to_monitoring": True,
        "pollutant_dust_kg": 1000.0,
        "pollutant_nox_kg": 500.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # Base 3,000,000 + (1000 * 0.8 + 500 * 0.8) = 3,001,200
    assert data["results"]["effective_fee_vnd"] == 3001200.0

    res_data = client.get(f"/api/v62/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "standard_calc" in d
    assert "no_monitoring_calc" in d
    assert "exempt_zero_calc" in d
    assert "exempt_out_calc" in d
