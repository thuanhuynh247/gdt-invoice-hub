"""Tests for US-364 and US-365 (Decree 132 Checklist & Transfer Pricing Risk Engine)."""

import pytest
from extensions import db
from invoices.models import Partner, Invoice
from invoices.v24_compliance_service import (
    calculate_related_party_disclosure,
    analyze_transfer_pricing_risk
)

def test_decree_132_disclosure_checklist_trigger_conditions(app):
    """US-364: Verify related party transaction triggers under Decree 132."""
    with app.app_context():
        # Clear existing data to avoid test interference
        Invoice.query.delete()
        Partner.query.delete()
        
        # 1. Register related partner
        p1 = Partner(mst="0101112223", name="Cong Ty Con A", address="Address A", decree_132_relationship="A")
        p2 = Partner(mst="0202223334", name="Nha Cung Cap B", address="Address B", decree_132_relationship="B")
        db.session.add_all([p1, p2])
        
        # 2. Add invoices below threshold (Revenue < 150B, Related transactions < 30B)
        # Revenue = 10B, Related transaction = 5B (sale to Cong Ty Con A)
        inv1 = Invoice(
            id="0108999999-C26TBA-00000001",
            seller_mst="0108999999", # taxpayer
            buyer_mst="0101112223",  # related
            amount_before_tax=5000000000.0, # 5B VND
            total_amount=5500000000.0,
            date="2026-06-05",
            imported_at="2026-06-05"
        )
        inv2 = Invoice(
            id="0108999999-C26TBA-00000002",
            seller_mst="0108999999", # taxpayer
            buyer_mst="8888888888",  # unrelated
            amount_before_tax=5000000000.0, # 5B VND
            total_amount=5500000000.0,
            date="2026-06-05",
            imported_at="2026-06-05"
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()
        
        # Check below threshold
        checklist = calculate_related_party_disclosure("0108999999", "2026-06-01", "2026-06-30")
        assert checklist["total_revenue"] == 10000000000.0 # 10B
        assert checklist["related_party_transactions"] == 5000000000.0 # 5B
        assert checklist["disclosure_required"] is False
        assert checklist["trigger_revenue"] is False
        assert checklist["trigger_transactions"] is False
        
        # 3. Add transactions to trigger transactions threshold >= 30B VND
        inv3 = Invoice(
            id="0108999999-C26TBA-00000003",
            seller_mst="0108999999", # taxpayer
            buyer_mst="0101112223",  # related
            amount_before_tax=26000000000.0, # 26B VND
            total_amount=28600000000.0,
            date="2026-06-10",
            imported_at="2026-06-10"
        )
        db.session.add(inv3)
        db.session.commit()
        
        checklist_triggered = calculate_related_party_disclosure("0108999999", "2026-06-01", "2026-06-30")
        assert checklist_triggered["related_party_transactions"] == 31000000000.0 # 31B VND
        assert checklist_triggered["disclosure_required"] is True
        assert checklist_triggered["trigger_transactions"] is True


def test_transfer_pricing_markup_risk_levels():
    """US-365: Verify comparison against lower, median and upper quartile statistical benchmarks."""
    # Benchmarks for Services: lower = 10%, median = 15%, upper = 20%
    tx_list = [
        # Margin = (50M - 46M) / 50M = 8% -> Below lower quartile (10%) -> HIGH RISK
        {"id": "TX_A", "partner_name": "Related Partner S1", "revenue": 50000000.0, "cogs": 46000000.0},
        # Margin = (100M - 85M) / 100M = 15% -> Equals median -> LOW RISK
        {"id": "TX_B", "partner_name": "Related Partner S2", "revenue": 100000000.0, "cogs": 85000000.0}
    ]
    
    analysis = analyze_transfer_pricing_risk(tx_list, "Services")
    
    assert analysis["verdict"] == "FLAGGED"
    assert analysis["high_risk_count"] == 1
    
    tx_a_result = next(tx for tx in analysis["analyzed_transactions"] if tx["transaction_id"] == "TX_A")
    assert tx_a_result["risk_level"] == "High Risk"
    assert "thấp hơn khoảng phần tư dưới" in tx_a_result["warning"]
    
    tx_b_result = next(tx for tx in analysis["analyzed_transactions"] if tx["transaction_id"] == "TX_B")
    assert tx_b_result["risk_level"] == "Low Risk"
    assert tx_b_result["warning"] == ""


def test_api_compliance_endpoints(client, logged_in_client, app):
    """Test Flask compliance endpoints for Decree 132 checklists and Transfer Pricing."""
    with app.app_context():
        # Register a partner
        p = Partner(mst="0108111222", name="Related Agent C", decree_132_relationship="C")
        db.session.add(p)
        db.session.commit()

    # 1. Test Decree 132 endpoint
    resp = logged_in_client.get(
        "/api/compliance/decree132-checklist?taxpayer_mst=0108999999&start_date=2026-06-01&end_date=2026-06-30"
    )
    assert resp.status_code == 200
    res_data = resp.get_json()
    assert "disclosure_required" in res_data
    
    # 2. Test Transfer Pricing Risk endpoint
    txs = [
        {"id": "T001", "partner_name": "Related Agent C", "revenue": 10000000.0, "cogs": 9800000.0}
    ]
    resp_tp = logged_in_client.post(
        "/api/compliance/transfer-pricing-risk",
        json={"transactions": txs, "sector": "Manufacturing"}
    )
    assert resp_tp.status_code == 200
    res_tp = resp_tp.get_json()
    assert res_tp["verdict"] == "FLAGGED"
    assert res_tp["high_risk_count"] == 1
