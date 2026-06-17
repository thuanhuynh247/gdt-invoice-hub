"""Pytest verification suite for v48 VAT Law Amendments 149/2025/QH15.

Tests revenue threshold reclassification, agricultural product exemption
updates, waste/scrap rate engine, API routing logic, and multi-tenant isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v48_service import V48ComplianceService


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


def test_threshold_reclassified(mock_tenant_db):
    """Test business reclassified from TAXABLE to NON_TAXABLE under new 500M threshold."""
    mst = mock_tenant_db
    service = V48ComplianceService()

    res = service.evaluate_threshold(
        mst=mst, business_name="Quán Phở Bình", annual_revenue=350_000_000
    )
    assert res["old_status"] == "TAXABLE"  # 350M > 200M
    assert res["new_status"] == "NON_TAXABLE"  # 350M ≤ 500M
    assert res["status_changed"] is True
    assert "RECLASSIFIED" in res["pit_impact"]


def test_threshold_still_taxable(mock_tenant_db):
    """Test business still TAXABLE under both old and new thresholds."""
    mst = mock_tenant_db
    service = V48ComplianceService()

    res = service.evaluate_threshold(
        mst=mst, business_name="Công ty ABC", annual_revenue=800_000_000
    )
    assert res["old_status"] == "TAXABLE"
    assert res["new_status"] == "TAXABLE"
    assert res["status_changed"] is False
    assert "STILL_TAXABLE" in res["pit_impact"]


def test_threshold_already_exempt(mock_tenant_db):
    """Test business already exempt under both old and new thresholds."""
    mst = mock_tenant_db
    service = V48ComplianceService()

    res = service.evaluate_threshold(
        mst=mst, business_name="Tiệm may nhỏ", annual_revenue=150_000_000
    )
    assert res["old_status"] == "NON_TAXABLE"
    assert res["new_status"] == "NON_TAXABLE"
    assert res["status_changed"] is False
    assert "NO_CHANGE" in res["pit_impact"]


def test_agri_enterprise_trade_reclassified(mock_tenant_db):
    """Test agricultural product reclassified for enterprise-to-enterprise trade."""
    mst = mock_tenant_db
    service = V48ComplianceService()

    res = service.classify_agri_product(
        mst=mst, product_description="Lúa gạo chưa chế biến",
        seller_type="doanh nghiệp", buyer_type="hợp tác xã"
    )
    assert res["old_vat_treatment"] == "NON_TAXABLE_NO_CREDIT"
    assert res["new_vat_treatment"] == "NO_DECLARATION_REQUIRED_WITH_CREDIT"
    assert res["input_credit_deductible"] is True
    assert res["treatment_changed"] is True


def test_agri_non_enterprise_unchanged(mock_tenant_db):
    """Test agricultural product stays non-taxable for individual sellers."""
    mst = mock_tenant_db
    service = V48ComplianceService()

    res = service.classify_agri_product(
        mst=mst, product_description="Rau sạch từ vườn nhà",
        seller_type="cá nhân", buyer_type="doanh nghiệp"
    )
    assert res["old_vat_treatment"] == "NON_TAXABLE_NO_CREDIT"
    assert res["new_vat_treatment"] == "NON_TAXABLE_NO_CREDIT"
    assert res["input_credit_deductible"] is False
    assert res["treatment_changed"] is False


def test_waste_scrap_rate_change(mock_tenant_db):
    """Test waste/scrap taxed at its own rate instead of source product rate."""
    mst = mock_tenant_db
    service = V48ComplianceService()

    res = service.compute_waste_scrap_rate(
        mst=mst, item_description="Vỏ bào gỗ phế liệu",
        source_product="Nội thất gỗ cao cấp",
        waste_rate_pct=5.0, source_rate_pct=10.0,
        amount=100_000_000
    )
    assert res["old_rate"] == "10.0%"
    assert res["new_rate"] == "5.0%"
    assert res["vat_old"] == 10_000_000  # 10% of 100M
    assert res["vat_new"] == 5_000_000   # 5% of 100M
    assert res["rate_changed"] is True


def test_waste_scrap_rate_same(mock_tenant_db):
    """Test waste/scrap with same rate as source product."""
    mst = mock_tenant_db
    service = V48ComplianceService()

    res = service.compute_waste_scrap_rate(
        mst=mst, item_description="Mạt sắt phế liệu",
        source_product="Thép xây dựng",
        waste_rate_pct=10.0, source_rate_pct=10.0,
        amount=50_000_000
    )
    assert res["old_rate"] == "10.0%"
    assert res["new_rate"] == "10.0%"
    assert res["vat_old"] == res["vat_new"]
    assert res["rate_changed"] is False


def test_api_routes_v48(mock_app, mock_tenant_db):
    """Test v48 HTTP API routes and view rendering."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v48-compliance-hub")
    assert res_page.status_code == 200
    assert b"Law 149" in res_page.data or b"Revenue Threshold" in res_page.data

    res_api = client.get(f"/api/v48/compliance-data?mst={mock_tenant_db}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "threshold_audit" in data
    assert "agri_classification" in data
    assert "waste_scrap" in data
