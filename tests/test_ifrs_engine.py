"""Test suite for IFRS Translation Engine and Compliance Endpoints (v18.0.0)."""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from extensions import db
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.ifrs_engine import IFRSTranslationService

@pytest.fixture
def mock_tenant_setup():
    """Fixture to ensure a clean tenant database for test taxpayer '0102030405'."""
    mst = "0102030405"
    db_path = get_tenant_db_path(mst)
    
    # Remove existing if any
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass
            
    # Bootstrap fresh DB
    bootstrap_tenant_db(mst)
    
    # Verify tables
    service = IFRSTranslationService()
    conn = service.get_tenant_connection(mst)
    cur = conn.cursor()
    
    # Clear tables and seed fresh mock deferred tax records
    cur.executescript("""
        DELETE FROM ifrs_deferred_tax_ledger;
        INSERT INTO ifrs_deferred_tax_ledger 
        (fiscal_year, fiscal_period, balance_sheet_item, carrying_amount_ifrs, tax_base_vas, tax_rate)
        VALUES 
        (2026, 12, 'Property, Plant and Equipment (Asset)', 1000000.0, 1200000.0, 0.20),
        (2026, 12, 'Accrued Liabilities (Liability)', 50000.0, 0.0, 0.20);
    """)
    conn.commit()
    conn.close()
    
    yield mst
    
    # Cleanup after test
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_ias12_deferred_tax_calculation(mock_tenant_setup):
    """Test IAS 12 Deferred Tax Asset and Liability rules."""
    mst = mock_tenant_setup
    service = IFRSTranslationService()
    
    records = service.calculate_ias12_deferred_tax(mst, 2026)
    
    assert len(records) == 2
    
    # First record: PPE Asset
    # Carrying = 1,000,000, Tax Base = 1,200,000
    # Carrying < Tax base -> Deferred Tax Asset = 200,000 * 20% = 40,000
    rec_asset = [r for r in records if "Asset" in r["balance_sheet_item"]][0]
    assert rec_asset["temporary_difference"] == -200000.0
    assert rec_asset["deferred_tax_asset"] == 40000.0
    assert rec_asset["deferred_tax_liability"] == 0.0
    
    # Second record: Accrued Liability
    # Carrying = 50,000, Tax Base = 0
    # Carrying > Tax base -> Deferred Tax Asset (since liability carrying > tax base means expense is tax-deferred)
    # diff = 50,000 - 0 = 50,000. Under liability rules, carrying > tax base -> deferred tax asset = 50,000 * 20% = 10,000
    rec_liab = [r for r in records if "Liability" in r["balance_sheet_item"]][0]
    assert rec_liab["temporary_difference"] == 50000.0
    assert rec_liab["deferred_tax_asset"] == 10000.0
    assert rec_liab["deferred_tax_liability"] == 0.0


def test_ifrs16_amortization_schedule():
    """Test IFRS 16 lease liability scheduling and present value computations."""
    service = IFRSTranslationService()
    
    # monthly payment = 1000, annual discount rate = 12% (1% monthly), term = 3 months
    schedule = service.calculate_ifrs16_amortization("lease-01", 1000.0, 0.12, 3)
    
    assert len(schedule) == 3
    # PV = 1000 * (1 - 1.01^-3) / 0.01 = 1000 * (1 - 0.97059) / 0.01 = 2940.97
    opening_bal = schedule[0]["opening_balance"]
    assert 2930.0 < opening_bal < 2950.0
    
    # Check that closing balance converges to 0 at the end
    assert schedule[-1]["closing_balance"] == 0.0


def test_pillar_two_topup_estimation(mock_tenant_setup):
    """Test OECD Pillar Two consolidated ETR and GloBE top-up estimations."""
    mst = mock_tenant_setup
    service = IFRSTranslationService()
    
    # Seed mock invoices to generate sales and VAT revenue for top-up ETR calculations
    conn = sqlite3.connect(get_tenant_db_path(mst))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO invoice (id, filename, seller_name, seller_mst, buyer_name, buyer_mst, amount_before_tax, tax_amount, total_amount, date, imported_at)
        VALUES 
        ('inv-01', 'mock_invoice.xml', 'Seller A', '0102030405', 'Buyer B', '1234567890', 100000.0, 10000.0, 110000.0, '2026-06-01', '2026-06-02T00:00:00Z');
    """)
    conn.commit()
    conn.close()
    
    res = service.estimate_pillar_two_topup("0102030405", [mst], 2026)
    
    # ETR = Taxes (income * 0.20) / Income -> should result in VN statutory rate of 20%
    assert res["consolidated_income"] == 100000.0
    assert res["effective_tax_rate"] == 0.20
    # Since 20% ETR >= 15% GloBE minimum rate, top-up tax rate should be 0.0
    assert res["topup_tax_rate"] == 0.0
    assert res["estimated_topup_tax"] == 0.0


def test_ias12_endpoint_authorized(logged_in_client, mock_tenant_setup):
    """Test authorized IAS 12 Deferred Tax endpoint execution."""
    mst = mock_tenant_setup
    
    payload = {
        "mst": mst,
        "year": 2026
    }
    
    resp = logged_in_client.post("/api/compliance/ias12-deferred-tax", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert len(data["records"]) == 2


def test_ifrs16_endpoint_authorized(logged_in_client):
    """Test authorized IFRS 16 Lease Schedule endpoint execution."""
    payload = {
        "lease_id": "lease-99",
        "monthly_payment": 2000.0,
        "discount_rate": 0.06,
        "lease_term_months": 12
    }
    
    resp = logged_in_client.post("/api/compliance/ifrs16-lease-schedule", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["lease_id"] == "lease-99"
    assert len(data["schedule"]) == 12


def test_pillar_two_endpoint_authorized(logged_in_client, mock_tenant_setup):
    """Test authorized Pillar Two top-up estimate endpoint execution."""
    mst = mock_tenant_setup
    
    payload = {
        "parent_mst": mst,
        "group_msts": [mst],
        "year": 2026
    }
    
    resp = logged_in_client.post("/api/compliance/pillar-two-estimate", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "estimate" in data
    assert data["estimate"]["parent_mst"] == mst
