"""Pytest verification suite for v50 PIT Law Amendments 109/2025/QH15.

Tests household business PIT exemption evaluation, progressive salary brackets PIT,
API routing, views, and database isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v50_service import V50ComplianceService


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


def test_household_pit_exemption(mock_tenant_db):
    """Test household PIT exemption evaluation based on 500M VND threshold."""
    mst = mock_tenant_db
    service = V50ComplianceService()

    # Exempt: revenue under 500M
    res1 = service.evaluate_household_pit(mst, "Tiem tap hoa A", 450_000_000, "distribution")
    assert res1["is_exempt"] is True
    assert res1["pit_liability"] == 0.0

    # Taxable: revenue over 500M - retail (0.5%)
    res2 = service.evaluate_household_pit(mst, "Cua hang B", 600_000_000, "distribution")
    assert res2["is_exempt"] is False
    assert res2["applied_rate"] == "0.5%"
    assert res2["pit_liability"] == 3_000_000

    # Taxable: services (2.0%)
    res3 = service.evaluate_household_pit(mst, "Spa Lam Dep", 800_000_000, "services")
    assert res3["is_exempt"] is False
    assert res3["applied_rate"] == "2.0%"
    assert res3["pit_liability"] == 16_000_000


def test_wage_progressive_pit(mock_tenant_db):
    """Test progressive salary PIT calculation with personal and dependent deductions."""
    mst = mock_tenant_db
    service = V50ComplianceService()

    # Monthly salary 35M, 2 dependents
    # Personal deduction: 15M, Dependents: 11M -> Total deduction = 26M
    # Taxable income = 35M - 26M = 9M
    # Bracket 1: 5M * 5% = 250,000
    # Bracket 2: 4M * 10% = 400,000
    # Total PIT = 650,000 VND
    res = service.calculate_wage_pit(mst, "Nguyen Van A", 35_000_000, 2)
    assert res["personal_deduction"] == 15_000_000
    assert res["dependent_deduction"] == 11_000_000
    assert res["total_deductions"] == 26_000_000
    assert res["taxable_income"] == 9_000_000
    assert res["calculated_pit"] == 650_000

    # Salary below deduction threshold
    res2 = service.calculate_wage_pit(mst, "Nguyen Van B", 12_000_000, 0)
    assert res2["taxable_income"] == 0.0
    assert res2["calculated_pit"] == 0.0


def test_api_routes_v50(mock_app, mock_tenant_db):
    """Test v50 HTTP API routes and view rendering."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v50-compliance-hub")
    assert res_page.status_code == 200
    assert b"Law 109" in res_page.data or b"PIT Amendments" in res_page.data

    res_api = client.get(f"/api/v50/compliance-data?mst={mock_tenant_db}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "household_evaluation" in data
    assert "wage_calculation" in data
