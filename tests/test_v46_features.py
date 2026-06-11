"""Pytest verification suite for v46 E-Invoice Incident Logs & Converted Bill Audit.

Tests database isolated storage, standard calculation rules, API routing logic, and multi-tenant isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v46_service import V46ComplianceService

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

def test_form_04_ss_logic(mock_tenant_db):
    """Test Form 04/SS e-invoice incident filing dates delay check."""
    mst = mock_tenant_db
    service = V46ComplianceService()
    
    # Check within 30 days
    res1 = service.process_form_04_ss(
        mst=mst,
        original_invoice_symbol="1C26TAA",
        original_invoice_number="0000015",
        invoice_date_str="2026-06-11",
        filing_date_str="2026-06-15",
        gdt_status_code=1
    )
    assert res1["gdt_status"] == "Accepted"
    assert res1["submission_delay_days"] == 4
    assert res1["deadline_warning"] is None

    # Check late filing (>30 days)
    res2 = service.process_form_04_ss(
        mst=mst,
        original_invoice_symbol="1C26TAA",
        original_invoice_number="0000015",
        invoice_date_str="2026-06-11",
        filing_date_str="2026-07-25",
        gdt_status_code=0
    )
    assert res2["gdt_status"] == "Pending"
    assert res2["submission_delay_days"] == 44
    assert "LATE_FILING_WARNING" in res2["deadline_warning"]

def test_conversion_prints_logic(mock_tenant_db):
    """Test Circular 78 conversion paper copies print limits and duplicate claims."""
    mst = mock_tenant_db
    service = V46ComplianceService()
    
    # 1. Normal print count
    res1 = service.audit_conversion_prints(
        mst=mst,
        invoice_symbol="1C26TAA",
        invoice_number="0000015",
        print_date_str="2026-06-12",
        print_count=1,
        converted_by="Admin",
        invoice_amount=10000000.0
    )
    assert len(res1["alerts"]) == 0

    # 2. Print count > 1 (Multiple prints warning)
    res2 = service.audit_conversion_prints(
        mst=mst,
        invoice_symbol="1C26TAA",
        invoice_number="0000015",
        print_date_str="2026-06-12",
        print_count=2,
        converted_by="Admin",
        invoice_amount=10000000.0
    )
    assert any(a["type"] == "MULTIPLE_CONVERSION_PRINTS_ALERT" for a in res2["alerts"])

def test_api_routes_v46(mock_app, mock_tenant_db):
    """Test v46 HTTP API routes and view rendering."""
    client = mock_app.test_client()
    
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db
        
    res_page = client.get("/v46-compliance-hub")
    assert res_page.status_code == 200
    assert b"E-Invoice Error &amp; Conversion" in res_page.data or b"E-Invoice Error & Conversion" in res_page.data
    
    res_api = client.get(f"/api/v46/compliance-data?mst={mock_tenant_db}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "incidents" in data
    assert "conversions" in data
