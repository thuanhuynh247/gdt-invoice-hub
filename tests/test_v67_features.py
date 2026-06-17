"""Pytest verification suite for v67 Scrap Import Environmental Deposit compliance.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v67_service import V67ComplianceService


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
    mst = "0102030467"
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


def test_scrap_deposit_steel(mock_tenant_db):
    """Steel scrap brackets: <500t (10%), 500-1000t (15%), >1000t (20%)."""
    service = V67ComplianceService()
    
    # 400t -> 10%
    res1 = service.calculate_deposit(mock_tenant_db, "Cargo 1", "scrap_steel", volume_tonnes=400.0, cargo_value_vnd=1000000.0)
    assert res1["deposit_rate"] == 0.10
    assert res1["deposit_amount"] == 100000.0

    # 600t -> 15%
    res2 = service.calculate_deposit(mock_tenant_db, "Cargo 2", "scrap_steel", volume_tonnes=600.0, cargo_value_vnd=1000000.0)
    assert res2["deposit_rate"] == 0.15
    assert res2["deposit_amount"] == 150000.0


def test_scrap_deposit_paper_plastic(mock_tenant_db):
    """Paper and Plastic brackets."""
    service = V67ComplianceService()

    # Paper 120t -> 18% (since it's between 100 and 500)
    res1 = service.calculate_deposit(mock_tenant_db, "Cargo Paper", "scrap_paper", volume_tonnes=120.0, cargo_value_vnd=2000000.0)
    assert res1["deposit_rate"] == 0.18
    assert res1["deposit_amount"] == 360000.0

    # Plastic 80t -> 18% (since it's under 100)
    res2 = service.calculate_deposit(mock_tenant_db, "Cargo Plastic", "scrap_plastic", volume_tonnes=80.0, cargo_value_vnd=3000000.0)
    assert res2["deposit_rate"] == 0.18
    assert res2["deposit_amount"] == 540000.0


def test_scrap_exemption(mock_tenant_db):
    """Research exemption: volume <= 5 tonnes."""
    service = V67ComplianceService()
    res = service.calculate_deposit(
        mock_tenant_db, "Lab sample", "scrap_plastic", volume_tonnes=4.5, cargo_value_vnd=50000000.0,
        exemption_category="laboratory_research"
    )
    assert res["is_exempt"] is True
    assert res["deposit_amount"] == 0.0


def test_scrap_history(mock_tenant_db):
    service = V67ComplianceService()
    service.calculate_deposit(mock_tenant_db, "Lô phế liệu sắt thép HP", "scrap_steel", volume_tonnes=600.0, cargo_value_vnd=5000000000.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["scrap_description"] == "Lô phế liệu sắt thép HP"


def test_api_routes_v67(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v67-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v67/calculate", json={
        "mst": mock_tenant_db,
        "scrap_description": "API Scrap",
        "scrap_type": "scrap_steel",
        "volume_tonnes": 600.0,
        "cargo_value_vnd": 100000000.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # Steel 600t -> 15%. Deposit = 100,000,000 * 0.15 = 15,000,000 VND
    assert data["results"]["deposit_amount"] == 15000000.0

    res_data = client.get(f"/api/v67/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "steel_standard" in d
    assert "plastic_standard" in d
    assert "research_exempt" in d
