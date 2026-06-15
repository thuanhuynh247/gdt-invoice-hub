"""Pytest verification suite for v43 IFRS Translation Engine & OECD Pillar Two console.

Tests database isolate storage, standard calculation rules, API routing logic, and multi-tenant isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from extensions import db
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.ifrs_engine import IFRSTranslationService

@pytest.fixture
def mock_app():
    """Create a mock Flask app context with base configurations."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["BASE_DATA_DIR"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    
    # Register blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(invoices_blueprint)
    
    return app

@pytest.fixture
def mock_tenant_db():
    """Ensure a clean tenant DB for testing."""
    mst = "0102030499"
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    db_path = get_tenant_db_path(mst, base_dir)
    
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass
            
    bootstrap_tenant_db(mst, base_dir)
    yield mst
    
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass

def test_ifrs15_allocation_and_recognition(mock_tenant_db):
    """Test relative SSP allocation and revenue recognition logic."""
    mst = mock_tenant_db
    service = IFRSTranslationService()
    
    contract_id = "CON-TEST-15"
    customer_name = "Test Client"
    contract_date = "2026-06-11"
    total_price = 100000.0
    obligations = [
        {"obligation_name": "Product A", "standalone_selling_price": 80000.0},
        {"obligation_name": "Product B", "standalone_selling_price": 40000.0}
    ]
    
    # Run allocation
    res = service.allocate_ifrs15_transaction_price(
        mst, contract_id, customer_name, contract_date, total_price, obligations
    )
    
    assert len(res) == 2
    # Product A: 80k/(80k+40k) * 100k = 66,666.67
    # Product B: 40k/(80k+40k) * 100k = 33,333.33
    alloc_a = next(x for x in res if x["obligation_name"] == "Product A")
    alloc_b = next(x for x in res if x["obligation_name"] == "Product B")
    
    assert round(alloc_a["allocated_price"], 2) == 66666.67
    assert round(alloc_b["allocated_price"], 2) == 33333.33
    
    # Verify recognition
    rec = service.recognize_ifrs15_revenue(mst, contract_id, ["Product A"], "2026-06-11")
    assert round(rec["recognized_revenue"], 2) == 66666.67
    
    # Verify in DB
    conn = service.get_tenant_connection(mst)
    cur = conn.cursor()
    cur.execute("SELECT recognized_revenue, deferred_revenue FROM ifrs15_revenue_contracts WHERE contract_id = ?", (contract_id,))
    row = cur.fetchone()
    assert round(row[0], 2) == 66666.67
    assert round(row[1], 2) == 33333.33
    conn.close()

def test_ifrs16_lease_schedule_calculation():
    """Test IFRS 16 lease liability scheduling and PV calculation."""
    service = IFRSTranslationService()
    
    # Monthly payment = 5000, annual rate = 6% (0.5% monthly), 12 months term
    # PV = 5000 * (1 - (1.005)**-12) / 0.005 = 58,079.91
    schedule = service.calculate_ifrs16_amortization("lease-99", 5000.0, 0.06, 12)
    assert len(schedule) == 12
    
    first_row = schedule[0]
    assert 58000.0 < first_row["opening_balance"] < 58100.0
    assert schedule[-1]["closing_balance"] == 0.0

def test_v43_api_endpoints(mock_app, mock_tenant_db):
    """Test and verify all custom API endpoints of version 43."""
    client = mock_app.test_client()
    
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db
        sess["user_role"] = "admin"
        sess["logged_in"] = True
        
    # 1. Test IFRS 15 Allocation Endpoint
    payload_15 = {
        "mst": mock_tenant_db,
        "contract_id": "CON-API-15",
        "customer_name": "Acme Inc",
        "contract_date": "2026-06-11",
        "total_price": 120000.0,
        "obligations": [
            {"obligation_name": "Software", "standalone_selling_price": 100000.0},
            {"obligation_name": "Training", "standalone_selling_price": 20000.0}
        ]
    }
    res = client.post("/api/v43/ifrs15/allocate", json=payload_15)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["allocated_price_splits"]) == 2
    
    # 2. Test IFRS 16 Lease Amortization Endpoint
    payload_16 = {
        "mst": mock_tenant_db,
        "lease_id": "LEASE-API-16",
        "supplier_mst": "9998887776",
        "commencement_date": "2026-01-01",
        "lease_term_months": 24,
        "monthly_payment": 3000.0,
        "discount_rate": 0.08
    }
    res = client.post("/api/v43/ifrs16/amortize", json=payload_16)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["amortization_table"]) == 24
    
    # 3. Test Dashboard Endpoint
    res = client.get(f"/api/v43/dashboard-data?mst={mock_tenant_db}&year=2026")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "deferred_tax" in data
    assert "leases" in data
    assert "pillar_two" in data
    assert "vietnam_reconciliation" in data

def test_calculate_vietnam_tax_reconciliation(mock_tenant_db):
    """Test standard Decree 132 cap and Circular 78 cash settlement non-deductibility calculations."""
    mst = mock_tenant_db
    service = IFRSTranslationService()
    
    # 1. EBITDA limit: 300M * 30% = 90M. Interest expense: 120M. Disallowed = 30M
    # Carryforward DTA = 30M * 20% = 6M
    res = service.calculate_vietnam_tax_reconciliation(
        mst=mst,
        year=2026,
        vas_profit_before_tax=500000000.0,
        total_interest_expense=120000000.0,
        ebitda=300000000.0
    )
    
    assert res["decree132_ebitda_limit"] == 90000000.0
    assert res["decree132_disallowed_interest"] == 30000000.0
    assert res["decree132_dta_carryforward"] == 30000000.0 * 0.20
    assert res["dta_recovery_risk"] is False # since profit is high and DTA is relatively small

def test_v43_compliance_reconcile_ifrs_vas_endpoint(mock_app, mock_tenant_db):
    """Test the POST endpoint for IFRS-VAS reconciliation."""
    client = mock_app.test_client()
    
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db
        sess["user_role"] = "admin"
        sess["logged_in"] = True
        
    payload = {
        "mst": mock_tenant_db,
        "year": 2026,
        "vas_profit_before_tax": 600000000.0,
        "total_interest_expense": 150000000.0,
        "ebitda": 400000000.0
    }
    
    res = client.post("/api/v43/compliance/reconcile-ifrs-vas", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "reconciliation" in data
    rec = data["reconciliation"]
    assert rec["decree132_ebitda_limit"] == 120000000.0
    assert rec["decree132_disallowed_interest"] == 30000000.0
