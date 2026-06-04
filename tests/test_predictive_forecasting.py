"""Tests for Predictive Cash Flow and Tax Forecasting Engine (US-110, US-111, US-324, US-325)."""

from __future__ import annotations

from invoices.tax_forecaster import (
    forecast_next_period_tax,
    TaxAlertManager,
    TaxForecastResult,
    ml_forecast_tax_liabilities,
    simulate_tax_scenario,
)


def test_forecast_empty_historical_data():
    """Empty historical data should return a default forecast result."""
    res = forecast_next_period_tax([], "2026-06")
    assert res.projected_period == "2026-06"
    assert res.projected_output_vat == 0.0
    assert res.projected_input_vat == 0.0
    assert res.projected_vat_payable == 0.0
    assert len(res.historical_periods_used) == 0


def test_forecast_calculation_with_trend():
    """Forecast calculation should incorporate moving averages and historical trends."""
    historical = [
        {"period": "2026-01", "output_vat": 10_000_000.0, "input_vat": 8_000_000.0},
        {"period": "2026-02", "output_vat": 12_000_000.0, "input_vat": 9_000_000.0},
        {"period": "2026-03", "output_vat": 15_000_000.0, "input_vat": 11_000_000.0},
    ]
    # alpha=0.7: weights moving average heavier than the trend adjustment
    res = forecast_next_period_tax(historical, "2026-04", alpha=0.7, window_size=3)

    assert res.projected_period == "2026-04"
    assert len(res.historical_periods_used) == 3
    assert res.projected_output_vat > 0.0
    assert res.projected_input_vat > 0.0
    assert res.projected_vat_payable == round(res.projected_output_vat - res.projected_input_vat, 2)


def test_alert_manager_below_limit():
    """Alerts should not trigger if forecasted VAT payable is under the budget threshold."""
    forecast = TaxForecastResult(
        projected_period="2026-04",
        projected_output_vat=100_000_000.0,
        projected_input_vat=80_000_000.0,
        projected_vat_payable=20_000_000.0,
        historical_periods_used=["2026-03"],
    )
    manager = TaxAlertManager(budget_limit=50_000_000.0)
    evaluated = manager.evaluate_forecast(forecast)

    assert evaluated.alert_triggered is False
    assert evaluated.alert_message == ""


def test_alert_manager_exceeds_limit():
    """Critical warnings should fire if projected tax liabilities exceed budgets."""
    forecast = TaxForecastResult(
        projected_period="2026-04",
        projected_output_vat=200_000_000.0,
        projected_input_vat=100_000_000.0,
        projected_vat_payable=100_000_000.0,
        historical_periods_used=["2026-03"],
    )
    manager = TaxAlertManager(budget_limit=50_000_000.0)
    evaluated = manager.evaluate_forecast(forecast)

    assert evaluated.alert_triggered is True
    assert "CẢNH BÁO" in evaluated.alert_message
    assert "vượt ngưỡng ngân sách" in evaluated.alert_message


def test_forecast_calculation():
    """Verify ML forecasting accuracy, trends, and seasonal confidence bounds (US-324)."""
    # Create historical data representing a simple upward trend
    historical_data = [
        {
            "period": f"2025-{month:02d}",
            "vat_payable": 10_000.0 * month,
            "cit_payable": 5_000.0 * month,
            "fct_payable": 1_000.0 * month,
        }
        for month in range(1, 13)
    ]
    
    forecasts = ml_forecast_tax_liabilities(historical_data, months_ahead=12)
    
    assert len(forecasts) == 12
    assert forecasts[0]["period"] == "2026-01"
    assert forecasts[11]["period"] == "2026-12"
    
    for f in forecasts:
        # Values should be non-negative
        assert f["predicted_vat_payable"] >= 0.0
        assert f["predicted_cit_payable"] >= 0.0
        assert f["predicted_fct_payable"] >= 0.0
        
        # Verify confidence intervals are wider for 95% than 80%
        # and bounds are correct (lower <= predicted <= upper)
        assert f["vat_lower_95"] <= f["vat_lower_80"]
        assert f["vat_lower_80"] <= f["predicted_vat_payable"]
        assert f["predicted_vat_payable"] <= f["vat_upper_80"]
        assert f["vat_upper_80"] <= f["vat_upper_95"]
        
        assert f["cit_lower_95"] <= f["cit_lower_80"]
        assert f["cit_lower_80"] <= f["predicted_cit_payable"]
        assert f["predicted_cit_payable"] <= f["cit_upper_80"]
        assert f["cit_upper_80"] <= f["cit_upper_95"]

        assert f["fct_lower_95"] <= f["fct_lower_80"]
        assert f["fct_lower_80"] <= f["predicted_fct_payable"]
        assert f["predicted_fct_payable"] <= f["fct_upper_80"]
        assert f["fct_upper_80"] <= f["fct_upper_95"]


def test_scenario_sandbox():
    """Verify tax scenario simulation sandbox adjustments, comparative calculations, and rules compliance (US-325)."""
    base_data = {
        "output_vat_base": 150_000_000.0,
        "input_vat_base": 100_000_000.0,
        "revenue_base": 2_000_000_000.0,
        "expenses_base": 1_500_000_000.0,
        "fct_base_amount": 100_000_000.0,
        "related_party_interest_base": 80_000_000.0,
        "depreciation_base": 120_000_000.0,
    }
    
    # 1. Base run (no adjustments)
    res_base = simulate_tax_scenario(base_data, adjustments={})
    assert res_base["original"]["vat"] == 50_000_000.0
    assert res_base["simulated"]["vat"] == 50_000_000.0
    assert res_base["variance"]["vat"] == 0.0
    assert res_base["percentage_change"]["vat"] == 0.0
    
    # 2. Adjustments run
    adjustments = {
        "tax_rate_vat": 8.0,
        "tax_rate_cit": 15.0,
        "tax_rate_fct": 3.0,
        "transfer_pricing_adjustment": 20_000_000.0,
        "tax_incentive_window": True,
        "cit_incentive_rate": 10.0,
    }
    
    res = simulate_tax_scenario(base_data, adjustments)
    
    # Original VAT should be output_vat_base - input_vat_base = 50,000,000.0
    # Simulated VAT should be (150M * 0.8) - (100M * 0.8) = 40,000,000.0
    assert res["original"]["vat"] == 50_000_000.0
    assert res["simulated"]["vat"] == 40_000_000.0
    assert res["variance"]["vat"] == -10_000_000.0
    assert res["percentage_change"]["vat"] == -20.0
    
    # Original FCT should be 100M * 5% = 5,000,000.0
    # Simulated FCT should be 100M * 3% = 3,000,000.0
    assert res["original"]["fct"] == 5_000_000.0
    assert res["simulated"]["fct"] == 3_000_000.0
    assert res["variance"]["fct"] == -2_000_000.0
    assert res["percentage_change"]["fct"] == -40.0
    
    # Original CIT calculation check (500M profit -> 20% CIT = 100,000,000.0)
    assert res["original"]["cit"] == 100_000_000.0
    
    # Simulated CIT calculation check
    # simulated expenses = 1.5B - 20M = 1.48B
    # pretax = 2B - 1.48B = 520M
    # simulated interest = 80M - 20M = 60M
    # EBITDA = 520M + 60M + 120M = 700M
    # interest cap = 700M * 30% = 210M -> interest expense (60M) < cap (210M) -> non-deductible = 0
    # taxable_income = 520M
    # simulated CIT with incentive active (10%) = 520M * 10% = 52,000,000.0
    assert res["simulated"]["cit"] == 52_000_000.0
    assert res["variance"]["cit"] == -48_000_000.0
    assert res["percentage_change"]["cit"] == -48.0

