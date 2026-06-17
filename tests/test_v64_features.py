"""Pytest verification suite for v64 Environment Protection Fee for Solid Waste (EPFSW).

Verifies solid waste protection fee calculations under Decree 164/2016/NĐ-CP, exemptions,
and REST APIs.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v64_service import V64ComplianceService


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


def test_epfsw_hazardous_standard(mock_tenant_db):
    """Hazardous Waste standard rate: 100,000 VND / tonne."""
    service = V64ComplianceService()
    res = service.calculate_epfsw(
        mock_tenant_db, "Chất thải nguy hại thạch cao", "hazardous_waste", volume_tonnes=15.0
    )
    assert res["base_rate"] == 100000.0
    # 15 * 100,000 = 1,500,000 VND
    assert res["total_fee_vnd"] == pytest.approx(1500000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(1500000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epfsw_ordinary_standard(mock_tenant_db):
    """Ordinary Industrial Waste standard rate: 40,000 VND / tonne."""
    service = V64ComplianceService()
    res = service.calculate_epfsw(
        mock_tenant_db, "Bụi lò luyện gang thông thường", "ordinary_waste_industry", volume_tonnes=120.0
    )
    assert res["base_rate"] == 40000.0
    # 120 * 40,000 = 4,800,000 VND
    assert res["total_fee_vnd"] == pytest.approx(4800000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(4800000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epfsw_exemptions(mock_tenant_db):
    """Exemptions under Decree 164/2016/NĐ-CP: self_recycled, agricultural_byproduct, domestic_rural."""
    service = V64ComplianceService()
    
    # Self recycled
    res_recycled = service.calculate_epfsw(
        mock_tenant_db, "Tro xỉ tự tái chế làm gạch khép kín", "ordinary_waste_industry", volume_tonnes=80.0, exemption_category="self_recycled"
    )
    assert res_recycled["is_exempt"] is True
    assert res_recycled["effective_fee_vnd"] == 0.0
    
    # Agricultural byproduct
    res_agri = service.calculate_epfsw(
        mock_tenant_db, "Rơm rạ phế phẩm làm phân hữu cơ", "ordinary_waste_others", volume_tonnes=45.0, exemption_category="agricultural_byproduct"
    )
    assert res_agri["is_exempt"] is True
    assert res_agri["effective_fee_vnd"] == 0.0

    # Domestic rural
    res_rural = service.calculate_epfsw(
        mock_tenant_db, "Rác sinh hoạt nông thôn", "ordinary_waste_others", volume_tonnes=5.0, exemption_category="domestic_rural"
    )
    assert res_rural["is_exempt"] is True
    assert res_rural["effective_fee_vnd"] == 0.0


def test_epfsw_history(mock_tenant_db):
    service = V64ComplianceService()
    service.calculate_epfsw(mock_tenant_db, "Waste batch", "ordinary_waste_construction", 50.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["waste_description"] == "Waste batch"


def test_api_routes_v64(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v64-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v64/calculate", json={
        "mst": mock_tenant_db,
        "waste_description": "API solid waste test",
        "waste_type": "ordinary_waste_construction",
        "volume_tonnes": 30.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # 30 * 30,000 = 900,000 VND
    assert data["results"]["effective_fee_vnd"] == 900000.0

    res_data = client.get(f"/api/v64/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "hazardous_standard" in d
    assert "ordinary_standard" in d
    assert "recycling_exempt" in d
    assert "agri_exempt" in d
