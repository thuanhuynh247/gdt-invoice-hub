"""Tests for Financial KPI Dashboard and Export Pipeline (US-114, US-115)."""

from __future__ import annotations

from invoices.financial_kpi import (
    calculate_financial_kpis,
    export_kpi_to_csv,
    FinancialKPIMetrics,
)


class TestFinancialKPI:
    """US-114, US-115: Financial KPI computations & CSV exporting."""

    def test_calculate_financial_kpis_basic(self):
        """Should calculate correct Gross Margin and Tax-to-Revenue ratios."""
        sales = [
            {"id": "S1", "amount_before_tax": 100_000_000, "tax_amount": 10_000_000, "date": "2026-05-01"},
            {"id": "S2", "amount_before_tax": 200_000_000, "tax_amount": 20_000_000, "date": "2026-05-02"},
        ]
        purchases = [
            {"id": "P1", "amount_before_tax": 150_000_000, "tax_amount": 15_000_000, "date": "2026-05-01"},
        ]

        # Sales: 300M, Cost: 150M -> Gross Margin = 50%
        # VAT output: 30M, VAT input: 15M -> VAT payable = 15M
        # Tax-to-revenue = 15M / 300M = 5%
        kpi = calculate_financial_kpis(sales, purchases)

        assert kpi.total_sales == 300_000_000.0
        assert kpi.cost_of_goods_sold == 150_000_000.0
        assert kpi.gross_margin_percent == 50.0
        assert kpi.vat_payable == 15_000_000.0
        assert kpi.tax_to_revenue_percent == 5.0
        assert kpi.invoice_count == 3

    def test_calculate_financial_kpis_empty(self):
        """Zero sales should avoid DivisionByZero and return zeroed metrics."""
        kpi = calculate_financial_kpis([], [])
        assert kpi.total_sales == 0.0
        assert kpi.cost_of_goods_sold == 0.0
        assert kpi.gross_margin_percent == 0.0
        assert kpi.vat_payable == 0.0
        assert kpi.tax_to_revenue_percent == 0.0

    def test_average_payment_period(self):
        """Should average the duration between invoice issuing and clearance."""
        sales = [
            {"id": "S1", "amount_before_tax": 10_000, "tax_amount": 1_000, "date": "2026-05-01"},
            {"id": "S2", "amount_before_tax": 20_000, "tax_amount": 2_000, "date": "2026-05-10"},
        ]
        clearances = [
            {"invoice_id": "S1", "clearance_date": "2026-05-05"}, # 4 days
            {"invoice_id": "S2", "clearance_date": "2026-05-20"}, # 10 days
        ]
        # Average: (4 + 10) / 2 = 7.0 days
        kpi = calculate_financial_kpis(sales, [], clearances)
        assert kpi.average_payment_period_days == 7.0

    def test_export_kpi_to_csv_content(self):
        """Export pipeline should output correctly formatted CSV content."""
        metrics = {
            "2026-05": FinancialKPIMetrics(
                total_sales=1000.0, cost_of_goods_sold=500.0, gross_margin_percent=50.0,
                vat_payable=50.0, tax_to_revenue_percent=5.0, average_payment_period_days=5.0,
                invoice_count=2,
            )
        }
        csv_str = export_kpi_to_csv(metrics)
        
        # Check CSV rows and header
        assert "Period" in csv_str
        assert "2026-05" in csv_str
        assert "1000.00" in csv_str
        assert "50.00" in csv_str
