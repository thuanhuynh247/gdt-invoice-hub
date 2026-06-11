"""Pytest verification suite for v49 CIT Law Amendments 67/2025/QH15.

Tests SME rates classification, real estate transfer loss offsetting, digital platform CIT withholding,
green exemptions, API routing logic, and multi-tenant database integration.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v49_service import V49ComplianceService


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


def test_sme_cit_rates(mock_tenant_db):
    """Test SME CIT rate classification based on revenue and TP status."""
    mst = mock_tenant_db
    service = V49ComplianceService()

    # Tier 1: under 3B
    res1 = service.classify_sme_cit(mst, "Company Tier 1", 2_500_000_000, False)
    assert res1["classified_rate"] == "15.0%"
    assert res1["is_sme"] is True

    # Tier 2: 3B to 50B
    res2 = service.classify_sme_cit(mst, "Company Tier 2", 10_000_000_000, False)
    assert res2["classified_rate"] == "17.0%"
    assert res2["is_sme"] is True

    # Tier 3: standard rate 20%
    res3 = service.classify_sme_cit(mst, "Company Standard", 60_000_000_000, False)
    assert res3["classified_rate"] == "20.0%"
    assert res3["is_sme"] is False

    # Disqualified via transfer pricing
    res4 = service.classify_sme_cit(mst, "Company Disqualified", 2_500_000_000, True)
    assert res4["classified_rate"] == "20.0%"
    assert res4["is_sme"] is False


def test_re_loss_offsetting(mock_tenant_db):
    """Test offsetting real estate losses against main production business income."""
    mst = mock_tenant_db
    service = V49ComplianceService()

    res = service.apply_re_loss_offset(mst, 2025, 1_000_000_000, 300_000_000)
    assert res["offset_applied"] == 300_000_000
    assert res["final_taxable_income"] == 700_000_000

    # Test where loss exceeds income
    res2 = service.apply_re_loss_offset(mst, 2025, 200_000_000, 500_000_000)
    assert res2["offset_applied"] == 200_000_000
    assert res2["final_taxable_income"] == 0.0


def test_digital_cit_withholding(mock_tenant_db):
    """Test auditing digital platform purchases and withholding rate logic."""
    mst = mock_tenant_db
    service = V49ComplianceService()

    # Foreign provider - service component (5%)
    res1 = service.audit_digital_cit(mst, "Google Ireland", True, 200_000_000, "service")
    assert res1["withholding_rate"] == "5.0%"
    assert res1["withholding_tax"] == 10_000_000

    # Foreign provider - trade component (1%)
    res2 = service.audit_digital_cit(mst, "Amazon Digital", True, 200_000_000, "trade")
    assert res2["withholding_rate"] == "1.0%"
    assert res2["withholding_tax"] == 2_000_000

    # Domestic provider - no withholding
    res3 = service.audit_digital_cit(mst, "VNG Cloud", False, 200_000_000, "service")
    assert res3["withholding_rate"] == "0.0%"
    assert res3["withholding_tax"] == 0.0


def test_green_exemptions(mock_tenant_db):
    """Test scanning green bond interest and carbon credit exemption status."""
    mst = mock_tenant_db
    service = V49ComplianceService()

    # Carbon credit
    res1 = service.scan_green_exemptions(mst, "First-time transfer of carbon credits", 150_000_000)
    assert res1["exemption_type"] == "carbon_credit"
    assert res1["is_exempt"] is True

    # Green bond
    res2 = service.scan_green_exemptions(mst, "Interest from green bonds issued 2025", 80_000_000)
    assert res2["exemption_type"] == "green_bond"
    assert res2["is_exempt"] is True

    # Standard transaction
    res3 = service.scan_green_exemptions(mst, "Office supplies purchase", 12_000_000)
    assert res3["exemption_type"] == "none"
    assert res3["is_exempt"] is False


def test_api_routes_v49(mock_app, mock_tenant_db):
    """Test v49 HTTP API routes and view rendering."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v49-compliance-hub")
    assert res_page.status_code == 200
    assert b"Law 67" in res_page.data or b"CIT Amendments" in res_page.data

    res_api = client.get(f"/api/v49/compliance-data?mst={mock_tenant_db}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "sme_classification" in data
    assert "re_loss_offset" in data
    assert "digital_audit" in data
    assert "green_exemption" in data
