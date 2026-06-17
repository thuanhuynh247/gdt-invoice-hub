"""Pytest verification suite for v70 Ozone-Depleting Substances (ODS) Quotas & Fees compliance.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v70_service import V70ComplianceService


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
    mst = "0102030470"
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


def test_ods_cfc_charge(mock_tenant_db):
    """CFC substance ODS charge: 250,000 VND/kg. ODP factor: 1.0."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "CFC batch 1", "cfc", weight_kg=100.0, exemption_category="none"
    )
    assert res["odp_factor"] == 1.0
    assert res["odp_weight_eq"] == 100.0
    assert res["license_charge_rate"] == 250000.0
    assert res["final_fee"] == 25000000.0
    assert res["is_exempt"] is False


def test_ods_low_volume_exemption(mock_tenant_db):
    """Low volume exemption: weight_kg < 50.0."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "CFC batch 2", "cfc", weight_kg=30.0, exemption_category="none"
    )
    assert res["is_exempt"] is True
    assert res["final_fee"] == 0.0


def test_ods_medical_exemption(mock_tenant_db):
    """Medical inhaler exemption (medical_use category)."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "Inhaler CFC gas", "cfc", weight_kg=200.0, exemption_category="medical_use"
    )
    assert res["is_exempt"] is True
    assert res["final_fee"] == 0.0


def test_ods_history(mock_tenant_db):
    service = V70ComplianceService()
    service.calculate_ods(mock_tenant_db, "Inhaler CFC gas", "cfc", weight_kg=200.0, exemption_category="medical_use")
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["substance_name"] == "Inhaler CFC gas"


def test_api_routes_v70(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v70-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v70/calculate", json={
        "mst": mock_tenant_db,
        "substance_name": "API ODS HCFC",
        "substance_group": "hcfc",
        "weight_kg": 200.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # HCFC ODP = 0.055. Licensing charge rate = 15,000 VND/kg.
    # final_fee = 200 * 15,000 = 3,000,000 VND.
    assert data["results"]["final_fee"] == 3000000.0

    res_data = client.get(f"/api/v70/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "cfc_standard" in d
    assert "hcfc_standard" in d
    assert "medical_exempt" in d
