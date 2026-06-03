"""Tests for Predictive Cash Flow and Tax Forecasting Engine (US-110, US-111)."""

from __future__ import annotations

from invoices.tax_forecaster import (
    forecast_next_period_tax,
    TaxAlertManager,
    TaxForecastResult,
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
