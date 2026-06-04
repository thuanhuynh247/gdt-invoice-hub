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


def ml_forecast_tax_liabilities(
    historical_data: list[dict],
    months_ahead: int = 12
) -> list[dict]:
    """US-324: Fit trend and seasonality on historical monthly aggregates to forecast
    monthly VAT, CIT, and FCT liabilities 12 months in advance.
    Includes 80% and 95% confidence intervals.
    """
    import math
    from datetime import datetime, timedelta

    if not historical_data:
        # Default empty response starting from current month
        start_date = datetime.now()
        forecast = []
        for i in range(1, months_ahead + 1):
            next_date = start_date + timedelta(days=30 * i)
            period = next_date.strftime("%Y-%m")
            forecast.append({
                "period": period,
                "predicted_vat_payable": 0.0,
                "vat_lower_80": 0.0,
                "vat_upper_80": 0.0,
                "vat_lower_95": 0.0,
                "vat_upper_95": 0.0,
                "predicted_cit_payable": 0.0,
                "cit_lower_80": 0.0,
                "cit_upper_80": 0.0,
                "cit_lower_95": 0.0,
                "cit_upper_95": 0.0,
                "predicted_fct_payable": 0.0,
                "fct_lower_80": 0.0,
                "fct_upper_80": 0.0,
                "fct_lower_95": 0.0,
                "fct_upper_95": 0.0,
            })
        return forecast

    # Parse periods and sort chronologically
    try:
        sorted_history = sorted(
            historical_data,
            key=lambda x: datetime.strptime(x["period"][:7], "%Y-%m")
        )
    except Exception:
        sorted_history = historical_data

    N = len(sorted_history)
    t = list(range(N))

    # Helper function for fitting a forecasting model for a target metric
    def fit_and_forecast_metric(metric_name: str) -> list[dict]:
        Y = []
        for item in sorted_history:
            Y.append(float(item.get(metric_name, 0.0)))

        # 1. Fit linear trend: y = beta0 + beta1 * x
        if N >= 2:
            mean_t = sum(t) / N
            mean_y = sum(Y) / N
            num = sum((t[i] - mean_t) * (Y[i] - mean_y) for i in range(N))
            den = sum((t[i] - mean_t) ** 2 for i in range(N))
            beta1 = num / den if den != 0.0 else 0.0
            beta0 = mean_y - beta1 * mean_t
        else:
            beta1 = 0.0
            beta0 = Y[0] if N == 1 else 0.0

        # 2. Fit seasonality (average residual per month of the year, 1 to 12)
        seasonal_factors = {m: 0.0 for m in range(1, 13)}
        if N >= 2:
            monthly_residuals = {m: [] for m in range(1, 13)}
            for i, item in enumerate(sorted_history):
                try:
                    dt = datetime.strptime(item["period"][:7], "%Y-%m")
                    m = dt.month
                except Exception:
                    m = (i % 12) + 1
                pred_trend = beta0 + beta1 * i
                residual = Y[i] - pred_trend
                monthly_residuals[m].append(residual)

            for m in range(1, 13):
                if monthly_residuals[m]:
                    seasonal_factors[m] = sum(monthly_residuals[m]) / len(monthly_residuals[m])

        # 3. Calculate residuals and standard error
        residuals = []
        for i, item in enumerate(sorted_history):
            try:
                dt = datetime.strptime(item["period"][:7], "%Y-%m")
                m = dt.month
            except Exception:
                m = (i % 12) + 1
            pred = beta0 + beta1 * i + seasonal_factors[m]
            residuals.append(Y[i] - pred)

        if N >= 3:
            residual_variance = sum(r ** 2 for r in residuals) / (N - 2)
            sigma = math.sqrt(max(0.0, residual_variance))
        elif N == 2:
            sigma = math.sqrt(sum(r ** 2 for r in residuals) / 2)
        else:
            # 1 or 0 points
            sigma = 0.1 * Y[0] if (N == 1 and Y[0] > 0.0) else 1000.0

        # Ensure sigma is not too small to avoid degenerate intervals
        mean_Y = sum(Y) / N if N > 0 else 1.0
        min_sigma = 0.15 * max(1000.0, mean_Y)
        if sigma < min_sigma:
            sigma = min_sigma

        # 4. Generate forecast for the next months_ahead periods
        # Find the last period in history to start predicting from
        try:
            last_date = datetime.strptime(sorted_history[-1]["period"][:7], "%Y-%m")
        except Exception:
            last_date = datetime.now()

        results = []
        for step in range(1, months_ahead + 1):
            # Calculate future period string using calendar logic
            month_offset = last_date.month - 1 + step
            future_year = last_date.year + (month_offset // 12)
            future_month = (month_offset % 12) + 1
            future_date = datetime(future_year, future_month, 1)
            future_period = future_date.strftime("%Y-%m")

            future_t = N - 1 + step
            # Forecast value
            pred_val = beta0 + beta1 * future_t + seasonal_factors[future_month]
            pred_val = max(0.0, round(pred_val, 2))

            # Forecast standard error
            if N >= 2:
                mean_t = sum(t) / N
                sum_sq_diff_t = sum((ti - mean_t) ** 2 for ti in t)
                if sum_sq_diff_t > 0:
                    se = sigma * math.sqrt(1 + (1 / N) + ((future_t - mean_t) ** 2 / sum_sq_diff_t))
                else:
                    se = sigma
            else:
                se = sigma

            # Confidence bounds (Z=1.282 for 80%, Z=1.960 for 95%)
            lower_80 = max(0.0, round(pred_val - 1.282 * se, 2))
            upper_80 = max(0.0, round(pred_val + 1.282 * se, 2))
            lower_95 = max(0.0, round(pred_val - 1.960 * se, 2))
            upper_95 = max(0.0, round(pred_val + 1.960 * se, 2))

            results.append({
                "period": future_period,
                "predicted": pred_val,
                "lower_80": lower_80,
                "upper_80": upper_80,
                "lower_95": lower_95,
                "upper_95": upper_95,
            })

        return results

    # Run for the three metrics
    vat_forecast = fit_and_forecast_metric("vat_payable")
    cit_forecast = fit_and_forecast_metric("cit_payable")
    fct_forecast = fit_and_forecast_metric("fct_payable")

    # Combine results
    combined_forecasts = []
    for idx in range(months_ahead):
        period = vat_forecast[idx]["period"]
        combined_forecasts.append({
            "period": period,
            "predicted_vat_payable": vat_forecast[idx]["predicted"],
            "vat_lower_80": vat_forecast[idx]["lower_80"],
            "vat_upper_80": vat_forecast[idx]["upper_80"],
            "vat_lower_95": vat_forecast[idx]["lower_95"],
            "vat_upper_95": vat_forecast[idx]["upper_95"],
            "predicted_cit_payable": cit_forecast[idx]["predicted"],
            "cit_lower_80": cit_forecast[idx]["lower_80"],
            "cit_upper_80": cit_forecast[idx]["upper_80"],
            "cit_lower_95": cit_forecast[idx]["lower_95"],
            "cit_upper_95": cit_forecast[idx]["upper_95"],
            "predicted_fct_payable": fct_forecast[idx]["predicted"],
            "fct_lower_80": fct_forecast[idx]["lower_80"],
            "fct_upper_80": fct_forecast[idx]["upper_80"],
            "fct_lower_95": fct_forecast[idx]["lower_95"],
            "fct_upper_95": fct_forecast[idx]["upper_95"],
        })

    return combined_forecasts


def simulate_tax_scenario(
    base_data: dict,
    adjustments: dict
) -> dict:
    """US-325: Run stateless simulation sandbox comparing original vs. simulated tax burdens.
    """
    # 1. Read baseline values
    output_vat_base = float(base_data.get("output_vat_base", 100_000_000.0))
    input_vat_base = float(base_data.get("input_vat_base", 80_000_000.0))
    revenue_base = float(base_data.get("revenue_base", 1_000_000_000.0))
    expenses_base = float(base_data.get("expenses_base", 800_000_000.0))
    fct_base_amount = float(base_data.get("fct_base_amount", 50_000_000.0))
    related_party_interest_base = float(base_data.get("related_party_interest_base", 30_000_000.0))
    depreciation_base = float(base_data.get("depreciation_base", 50_000_000.0))
    
    # Standard rates
    vat_rate_base = 10.0
    cit_rate_base = 20.0
    fct_rate_base = 5.0
    
    # Compute original liabilities
    orig_vat = max(0.0, output_vat_base - input_vat_base)
    
    orig_pretax_profit = revenue_base - expenses_base
    orig_ebitda = max(0.0, orig_pretax_profit + related_party_interest_base + depreciation_base)
    orig_interest_cap = orig_ebitda * 0.3
    orig_non_deductible_interest = max(0.0, related_party_interest_base - orig_interest_cap)
    
    orig_taxable_income = orig_pretax_profit + orig_non_deductible_interest
    orig_cit = max(0.0, orig_taxable_income * (cit_rate_base / 100.0))
    
    orig_fct = max(0.0, fct_base_amount * (fct_rate_base / 100.0))
    orig_total = orig_vat + orig_cit + orig_fct
    
    # 2. Apply simulated adjustments
    sim_vat_rate = float(adjustments.get("tax_rate_vat", vat_rate_base))
    sim_cit_rate = float(adjustments.get("tax_rate_cit", cit_rate_base))
    sim_fct_rate = float(adjustments.get("tax_rate_fct", fct_rate_base))
    tp_adjust = float(adjustments.get("transfer_pricing_adjustment", 0.0))
    incentive_active = bool(adjustments.get("tax_incentive_window", False))
    cit_inc_rate = float(adjustments.get("cit_incentive_rate", 10.0))
    
    # Scale VAT based on rate difference
    vat_scale = sim_vat_rate / 10.0
    sim_output_vat = output_vat_base * vat_scale
    sim_input_vat = input_vat_base * vat_scale
    sim_vat = max(0.0, sim_output_vat - sim_input_vat)
    
    # Adjust simulated CIT
    sim_expenses = expenses_base - tp_adjust
    sim_pretax_profit = revenue_base - sim_expenses
    
    sim_interest = max(0.0, related_party_interest_base - tp_adjust)
    sim_ebitda = max(0.0, sim_pretax_profit + sim_interest + depreciation_base)
    sim_interest_cap = sim_ebitda * 0.3
    sim_non_deductible_interest = max(0.0, sim_interest - sim_interest_cap)
    
    sim_taxable_income = sim_pretax_profit + sim_non_deductible_interest
    effective_cit_rate = cit_inc_rate if incentive_active else sim_cit_rate
    sim_cit = max(0.0, sim_taxable_income * (effective_cit_rate / 100.0))
    
    sim_fct = max(0.0, fct_base_amount * (sim_fct_rate / 100.0))
    sim_total = sim_vat + sim_cit + sim_fct
    
    # Calculate variances
    variance_vat = sim_vat - orig_vat
    variance_cit = sim_cit - orig_cit
    variance_fct = sim_fct - orig_fct
    variance_total = sim_total - orig_total
    
    # Risk and validation checks (Decree 132/Decree 126/etc.)
    warnings = []
    risk_level = "Low"
    
    if sim_non_deductible_interest > 0:
        warnings.append("Cảnh báo: Chi phí lãi vay vượt trần 30% EBITDA theo Nghị định 132.")
        risk_level = "Medium"
    if sim_pretax_profit < 0:
        warnings.append("Cảnh báo: Doanh nghiệp lỗ trước thuế sau điều chỉnh.")
        risk_level = "High"
    if tp_adjust > (expenses_base * 0.2):
        warnings.append("Cảnh báo: Khoản điều chỉnh giá giao dịch liên kết lớn (>20% tổng chi phí). Cần lưu giữ đầy đủ hồ sơ xác định giá giao dịch liên kết.")
        risk_level = "High"

    return {
        "original": {
            "vat": round(orig_vat, 2),
            "cit": round(orig_cit, 2),
            "fct": round(orig_fct, 2),
            "total": round(orig_total, 2),
        },
        "simulated": {
            "vat": round(sim_vat, 2),
            "cit": round(sim_cit, 2),
            "fct": round(sim_fct, 2),
            "total": round(sim_total, 2),
        },
        "variance": {
            "vat": round(variance_vat, 2),
            "cit": round(variance_cit, 2),
            "fct": round(variance_fct, 2),
            "total": round(variance_total, 2),
        },
        "percentage_change": {
            "vat": round((variance_vat / orig_vat * 100) if orig_vat > 0 else 0.0, 2),
            "cit": round((variance_cit / orig_cit * 100) if orig_cit > 0 else 0.0, 2),
            "fct": round((variance_fct / orig_fct * 100) if orig_fct > 0 else 0.0, 2),
            "total": round((variance_total / orig_total * 100) if orig_total > 0 else 0.0, 2),
        },
        "warnings": warnings,
        "risk_level": risk_level
    }

