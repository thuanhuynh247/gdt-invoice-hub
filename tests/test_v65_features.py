"""Pytest verification suite for v65 Extended Producer Responsibility (EPR) recycling fee.

Verifies EPR contributions under Decree 08/2022/NĐ-CP, product categories, recycling rates,
exemptions, and REST APIs.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v65_service import V65ComplianceService


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


def test_epr_plastic_standard(mock_tenant_db):
    """Plastic Packaging standard: R=22%, Fs=8000 VND/kg."""
    service = V65ComplianceService()
    res = service.calculate_epr(
        mock_tenant_db, "Bao bì nhựa PP đóng gói đường", "packaging_plastic", volume_kg=100000.0
    )
    assert res["recycling_rate"] == 0.22
    assert res["cost_coefficient"] == 8000.0
    # 0.22 * 100,000 * 8,000 = 176,000,000 VND
    assert res["total_fee_vnd"] == pytest.approx(176000000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(176000000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epr_paper_standard(mock_tenant_db):
    """Paper Carton Packaging standard: R=15%, Fs=2500 VND/kg."""
    service = V65ComplianceService()
    res = service.calculate_epr(
        mock_tenant_db, "Hộp carton đựng sữa tiệt trùng", "packaging_paper_carton", volume_kg=250000.0
    )
    assert res["recycling_rate"] == 0.15
    assert res["cost_coefficient"] == 2500.0
    # 0.15 * 250,000 * 2,500 = 93,750,000 VND
    assert res["total_fee_vnd"] == pytest.approx(93750000.0, rel=1e-3)
    assert res["effective_fee_vnd"] == pytest.approx(93750000.0, rel=1e-3)
    assert res["is_exempt"] is False


def test_epr_exemptions(mock_tenant_db):
    """Exemptions under Decree 08/2022/NĐ-CP: small_scale_revenue, small_scale_import, closed_loop_recycling, export_only."""
    service = V65ComplianceService()
    
    # Small scale revenue
    res_revenue = service.calculate_epr(
        mock_tenant_db, "Bao bì nhựa của cơ sở nhỏ lẻ", "packaging_plastic", volume_kg=15000.0,
        annual_revenue_vnd=25000000000.0, exemption_category="small_scale_revenue"
    )
    assert res_revenue["is_exempt"] is True
    assert res_revenue["effective_fee_vnd"] == 0.0

    # Small scale import
    res_import = service.calculate_epr(
        mock_tenant_db, "Hộp carton nhập khẩu nhỏ lẻ", "packaging_paper_carton", volume_kg=10000.0,
        annual_import_vnd=15000000000.0, exemption_category="small_scale_import"
    )
    assert res_import["is_exempt"] is True
    assert res_import["effective_fee_vnd"] == 0.0
    
    # Closed loop recycling
    res_closed = service.calculate_epr(
        mock_tenant_db, "Ắc quy chì thu hồi tái chế khép kín", "battery_lead_acid", volume_kg=50000.0,
        exemption_category="closed_loop_recycling"
    )
    assert res_closed["is_exempt"] is True
    assert res_closed["effective_fee_vnd"] == 0.0

    # Export only
    res_export = service.calculate_epr(
        mock_tenant_db, "Vỏ hộp xuất khẩu", "packaging_plastic", volume_kg=20000.0,
        exemption_category="export_only"
    )
    assert res_export["is_exempt"] is True
    assert res_export["effective_fee_vnd"] == 0.0


def test_epr_history(mock_tenant_db):
    service = V65ComplianceService()
    service.calculate_epr(mock_tenant_db, "Lubricant batch", "lubricant_oil", 5000.0)
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["product_description"] == "Lubricant batch"


def test_api_routes_v65(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v65-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v65/calculate", json={
        "mst": mock_tenant_db,
        "product_description": "API EPR test",
        "product_type": "lubricant_oil",
        "volume_kg": 20000.0,
        "annual_revenue_vnd": 35000000000.0,
        "annual_import_vnd": 25000000000.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # R=10%, Fs=5000 -> 0.10 * 20000 * 5000 = 10,000,000 VND
    assert data["results"]["effective_fee_vnd"] == 10000000.0

    res_data = client.get(f"/api/v65/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "plastic_standard" in d
    assert "paper_standard" in d
    assert "small_revenue_exempt" in d
    assert "closed_loop_exempt" in d
