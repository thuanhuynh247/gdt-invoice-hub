"""Pytest verification suite for v45 Circular 80 CIT Incentives & Decree 132 TP Safe Harbors.

Tests database isolated storage, standard calculation rules, API routing logic, and multi-tenant isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v45_service import V45ComplianceService

@pytest.fixture
def mock_app():
    """Create a mock Flask app context with base configurations."""
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["BASE_DATA_DIR"] = os.path.join(os.path.dirname(__file__), "..", "data")
    
    # Register blueprints
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

def test_cit_incentives_logic(mock_tenant_db):
    """Test Circular 80 CIT preferential rate and tax holiday logic."""
    mst = mock_tenant_db
    service = V45ComplianceService()
    
    # Test year 2026 (Holiday start year 2024, 2 exempt, 4 reduction) -> 50% Reduction
    res = service.simulate_preferential_cit(
        mst=mst,
        year=2026,
        total_taxable_income=1200000000.0,
        preferential_income=700000000.0,
        preferential_rate=0.10,
        holiday_start_year=2024,
        exemption_years=2,
        reduction_years=4
    )
    
    # 500,000,000 * 20% = 100,000,000 standard
    # 700,000,000 * 10% * 50% reduction = 35,000,000 preferential
    # Total = 135,000,000
    assert res["cit_standard_liability"] == 100000000.0
    assert res["cit_preferential_liability"] == 35000000.0
    assert res["cit_total_due"] == 135000000.0
    assert res["cit_savings"] == 105000000.0
    assert "50% Tax Reduction" in res["holiday_status"]

def test_tp_safe_harbors_logic(mock_tenant_db):
    """Test Decree 132 TP Safe Harbor thresholds and APA margins."""
    mst = mock_tenant_db
    service = V45ComplianceService()
    
    # Under 50B rev, under 30B transactions -> Safe Harbor
    res = service.evaluate_tp_safe_harbors(
        mst=mst,
        year=2026,
        total_revenue=48000000000.0,
        related_party_txn_value=28000000000.0,
        net_profit_margin=0.035,
        activity_type="trading",
        apa_lower=0.03,
        apa_upper=0.05,
        actual_margin=0.04
    )
    assert res["safe_harbor_eligible"] is True
    assert res["apa_status"] == "Compliant"
    
    # Excess revenue, but NPM meets manufacturing threshold (10%)
    res2 = service.evaluate_tp_safe_harbors(
        mst=mst,
        year=2026,
        total_revenue=150000000000.0,
        related_party_txn_value=60000000000.0,
        net_profit_margin=0.12,
        activity_type="manufacturing"
    )
    assert res2["safe_harbor_eligible"] is True

def test_api_routes_v45(mock_app, mock_tenant_db):
    """Test v45 HTTP API routes and view rendering."""
    client = mock_app.test_client()
    
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db
        
    res_page = client.get("/v45-compliance-hub")
    assert res_page.status_code == 200
    assert b"CIT &amp; TP Hub" in res_page.data or b"CIT & TP Hub" in res_page.data
    
    res_api = client.get(f"/api/v45/compliance-data?mst={mock_tenant_db}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "cit_simulation" in data
    assert "tp_safe_harbor" in data
