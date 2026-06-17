"""Pytest verification suite for v44 Decree 123 VAT Adjustment & Circular 67 Sci-Tech Fund Optimizer.

Tests database isolated storage, standard calculation rules, API routing logic, and multi-tenant isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v44_service import V44ComplianceService

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

def test_decree123_vat_adjustment_logic(mock_tenant_db):
    """Test Decree 123 VAT adjustment and discount matching rules."""
    mst = mock_tenant_db
    service = V44ComplianceService()
    
    # Seed mock invoices in tenant DB first
    conn = service.get_tenant_connection(mst)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO invoice (id, filename, seller_name, seller_mst, buyer_name, buyer_mst, amount_before_tax, tax_amount, total_amount, date, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("0000015", "invoice_0000015.xml", "This Corp", mst, "Acme Client", "0102030499", 100000000.0, 1000000.0, 110000000.0, "2026-06-11", "2026-06-11"))
    
    # Seed mock adjustment row that's valid
    cur.execute("""
        INSERT INTO decree123_invoice_adjustments 
        (original_invoice_symbol, original_invoice_number, adjustment_invoice_symbol, adjustment_invoice_number, adjustment_type, amount_change, vat_change, tax_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("1C26TAA", "0000015", "1C26TAA", "0000088", "adjustment", -10000000.0, -100000.0, 0.10))
    
    # Seed mock adjustment row that's invalid due to exceeding amount
    cur.execute("""
        INSERT INTO decree123_invoice_adjustments 
        (original_invoice_symbol, original_invoice_number, adjustment_invoice_symbol, adjustment_invoice_number, adjustment_type, amount_change, vat_change, tax_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("1C26TAA", "0000015", "1C26TAA", "0000122", "adjustment", -500000000.0, -50000000.0, 0.10))

    # Seed mock adjustment row that's unlinked
    cur.execute("""
        INSERT INTO decree123_invoice_adjustments 
        (original_invoice_symbol, original_invoice_number, adjustment_invoice_symbol, adjustment_invoice_number, adjustment_type, amount_change, vat_change, tax_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("INVALID", "9999999", "3C26TCC", "0000100", "replacement", -20000000.0, -2000000.0, 0.10))

    conn.commit()
    conn.close()
    
    results = service.reconcile_decree123_adjustments(mst)
    assert len(results) == 3
    
    valid_adj = next(r for r in results if r["adjustment_invoice_number"] == "0000088")
    assert valid_adj["status"] == "Linked"
    
    invalid_adj = next(r for r in results if r["adjustment_invoice_number"] == "0000122")
    assert invalid_adj["status"] == "Mismatch"
    assert "exceed" in invalid_adj["mismatch_reason"]
    
    unlinked_adj = next(r for r in results if r["adjustment_invoice_number"] == "0000100")
    assert unlinked_adj["status"] == "Unlinked"

def test_sci_tech_fund_simulation(mock_tenant_db):
    """Test Circular 67 and Circular 05 fund calculation and clawbacks."""
    mst = mock_tenant_db
    service = V44ComplianceService()
    
    # 10% of 1,000,000,000 is 100,000,000 limit
    res = service.simulate_sci_tech_fund(
        mst=mst,
        year=2026,
        taxable_income=1000000000.0,
        allocation_percent=10.0,
        annual_rd_spend=15000000.0,   # Spend 15M/year
        qualified_ratio=0.8,          # 80% qualified -> 12M qualified spent/year
        welfare_expenses=20000000.0,
        average_monthly_salary=15000000.0
    )
    
    assert res["allocated_amount"] == 100000000.0
    # Total qualified spent = 12M * 5 years = 60,000,000 VND
    assert res["total_qualified_spent"] == 60000000.0
    # Remaining unspent balance = 100M - 60M = 40,000,000 VND
    assert res["unspent_amount"] == 40000000.0
    # CIT Clawback = 40M * 20% = 8,000,000 VND
    assert res["cit_clawback"] == 8000000.0
    # Late Payment Interest = 8,000,000 * 0.0003 * 1825 = 4,380,000 VND
    assert res["late_interest_penalty"] == 4380000.0
    # Welfare mismatch = 20M - 15M = 5,000,000 VND
    assert res["welfare_mismatch_non_deductible"] == 5000000.0

def test_api_routes(mock_app, mock_tenant_db):
    """Test compliance API routing and templates rendering."""
    client = mock_app.test_client()
    
    # Set session login
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db
        
    # Get v44 dashboard template page
    res_page = client.get("/v44-compliance-hub")
    assert res_page.status_code == 200
    assert b"Compliance Hub" in res_page.data
    
    # Get v44 dashboard initial API payload
    res_api = client.get(f"/api/v44/compliance-data?mst={mock_tenant_db}&year=2026")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "reconciliation" in data
    assert "simulation" in data
    
    # Post adjustment reconcile
    res_rec = client.post("/api/v44/reconcile-adjustments", json={"mst": mock_tenant_db})
    assert res_rec.status_code == 200
    rec_data = json.loads(res_rec.data)
    assert rec_data["status"] == "success"
    
    # Post simulation recalculate
    res_sim = client.post("/api/v44/sci-tech-fund/simulate", json={
        "mst": mock_tenant_db,
        "year": 2026,
        "taxable_income": 1200000000.0,
        "allocation_percent": 8.0,
        "annual_rd_spend": 20000000.0,
        "qualified_ratio": 0.9,
        "welfare_expenses": 10000000.0,
        "average_monthly_salary": 12000000.0
    })
    assert res_sim.status_code == 200
    sim_data = json.loads(res_sim.data)
    assert sim_data["status"] == "success"
    assert sim_data["simulation_results"]["allocated_amount"] == 96000000.0
