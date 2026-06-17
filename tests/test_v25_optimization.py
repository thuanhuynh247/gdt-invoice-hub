"""Tests for US-374 and US-375 (Corporate Tax Optimization Scenario Modeler Engine)."""

import pytest
from extensions import db
from invoices.models import Invoice
from invoices.v25_compliance_service import calculate_corporate_tax_optimization

def test_calculate_corporate_tax_optimization(app):
    """US-374: Run tax optimization and scenario simulations on taxpayer's financial data."""
    with app.app_context():
        # Clear invoices
        db.session.query(Invoice).delete()
        db.session.commit()

        # Add a few invoices for taxpayer to establish baseline
        mst = "0108999999"
        
        # Sales invoices (income)
        db.session.add(Invoice(
            id="0108999999-C26TBA-00000001",
            number="00000001",
            symbol="C26TBA",
            template_code="1",
            date="2026-06-05",
            seller_mst=mst,
            buyer_mst="0200112233",
            amount_before_tax=100000000000.0, # 100B
            total_amount=110000000000.0,
            has_signature=True,
            imported_at="2026-06-05T00:00:00"
        ))
        
        # Purchase invoices (expenses)
        db.session.add(Invoice(
            id="0300112233-C26TBA-00000002",
            number="00000002",
            symbol="C26TBA",
            template_code="1",
            date="2026-06-05",
            seller_mst="0300112233",
            buyer_mst=mst,
            amount_before_tax=60000000000.0, # 60B
            total_amount=66000000000.0,
            payment_method="TM", # CASH (warning / non-deductible because >20M and TM)
            has_signature=True,
            imported_at="2026-06-05T00:00:00"
        ))
        
        db.session.commit()
        
        # Run scenarios
        scenarios = [
            {
                "name": "Kịch bản tối ưu 1: Áp dụng thuế ưu đãi 10% & Miễn thuế 2 năm",
                "preferential_rate": 0.10,
                "holiday_exempt_years": 2,
                "holiday_reduce_years": 4,
                "reduce_loan_interest": True,
                "enforce_bank_transfer": True
            },
            {
                "name": "Kịch bản tối ưu 2: Ưu đãi 15% & Giảm thuế 50%",
                "preferential_rate": 0.15,
                "holiday_exempt_years": 0,
                "holiday_reduce_years": 2,
                "reduce_loan_interest": False,
                "enforce_bank_transfer": False
            }
        ]
        
        report = calculate_corporate_tax_optimization(mst, scenarios)
        
        assert report["taxpayer_mst"] == mst
        assert "baseline" in report
        assert "scenarios" in report
        assert len(report["scenarios"]) == 2
        
        best = report["best_scenario"]
        assert best is not None
        # Best scenario should be scenario 1 because of tax exemption (exemption years > 0)
        assert best["scenario_name"] == "Kịch bản tối ưu 1: Áp dụng thuế ưu đãi 10% & Miễn thuế 2 năm"
        assert best["cit_liability"] == 0.0
        assert best["tax_savings"] > 0.0
