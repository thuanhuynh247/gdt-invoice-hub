# Story Specification: US-324 — Machine Learning Tax Liability Predictor

## 📋 Context & Business Value
To improve corporate financial planning, the system uses machine learning regression (or structured time series forecasting) to predict monthly VAT and CIT liabilities 12 months in advance, including upper/lower confidence bounds.

---

## 🎯 Acceptance Criteria
- **Model Training**: Ingest historical invoice monthly aggregates to fit trend and seasonality.
- **Forecasting Output**: Return array of predicted monthly values with 80% and 95% confidence intervals.
- **API Endpoint**:
  - `POST /api/predictive/tax-forecast` to retrieve predictive tax liability reports.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying forecasting accuracy and confidence bounds:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_predictive_forecasting.py -k test_forecast_calculation"
  ```
