"""Predictive Tax and Cash Flow Forecasting Engine (US-110, US-111).

Provides seasonal moving average calculations with trend adjustments to forecast
future VAT liabilities. Includes budget threshold alerts for projected taxes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class TaxForecastResult:
    """Result of a predictive tax forecast run."""
    projected_period: str
    projected_output_vat: float
    projected_input_vat: float
    projected_vat_payable: float
    historical_periods_used: list[str]
    alert_triggered: bool = False
    alert_message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def forecast_next_period_tax(
    historical_data: list[dict],
    projected_period: str,
    alpha: float = 0.7,
    window_size: int = 3,
) -> TaxForecastResult:
    """Forecast future VAT outputs and inputs using a trend-adjusted moving average.

    historical_data is a list of dicts, sorted chronologically:
      [{"period": "2026-01", "output_vat": 100.0, "input_vat": 80.0}, ...]
    """
    if not historical_data:
        return TaxForecastResult(
            projected_period=projected_period,
            projected_output_vat=0.0,
            projected_input_vat=0.0,
            projected_vat_payable=0.0,
            historical_periods_used=[],
        )

    # Use the last `window_size` periods
    subset = historical_data[-window_size:]
    periods = [item["period"] for item in subset]

    # Calculate basic moving averages
    avg_output = sum(item["output_vat"] for item in subset) / len(subset)
    avg_input = sum(item["input_vat"] for item in subset) / len(subset)

    # Calculate trends (difference between last and first in window, if multiple)
    trend_output = 0.0
    trend_input = 0.0
    if len(subset) > 1:
        trend_output = subset[-1]["output_vat"] - subset[0]["output_vat"]
        trend_input = subset[-1]["input_vat"] - subset[0]["input_vat"]

    # Forecast = alpha * MA + (1 - alpha) * (last + trend)
    last_output = subset[-1]["output_vat"]
    last_input = subset[-1]["input_vat"]

    proj_output = alpha * avg_output + (1.0 - alpha) * (last_output + trend_output)
    proj_input = alpha * avg_input + (1.0 - alpha) * (last_input + trend_input)

    # Tax cannot be negative in projection, round to 2 decimals
    proj_output = max(0.0, round(proj_output, 2))
    proj_input = max(0.0, round(proj_input, 2))
    proj_payable = round(proj_output - proj_input, 2)

    return TaxForecastResult(
        projected_period=projected_period,
        projected_output_vat=proj_output,
        projected_input_vat=proj_input,
        projected_vat_payable=proj_payable,
        historical_periods_used=periods,
    )


class TaxAlertManager:
    """Configures thresholds and evaluates alerts on forecasted tax results."""

    def __init__(self, budget_limit: float = 500_000_000.0):
        self.budget_limit = budget_limit

    def evaluate_forecast(self, forecast: TaxForecastResult) -> TaxForecastResult:
        """Flag alert if projected VAT payable exceeds the budget limit."""
        if forecast.projected_vat_payable > self.budget_limit:
            forecast.alert_triggered = True
            forecast.alert_message = (
                f"CẢNH BÁO: Thuế GTGT dự kiến phải nộp ({forecast.projected_vat_payable:,.0f} VND) "
                f"vượt ngưỡng ngân sách doanh nghiệp ({self.budget_limit:,.0f} VND)."
            )
        return forecast
