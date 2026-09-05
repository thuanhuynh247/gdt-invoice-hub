# Execution Plan: TimesFM Supplier Tax & Fee Time-Series Forecasting Engine

## Phase 1: Core Engine Implementation (`invoices/timesfm_engine.py`)
1. Build `TimesFMPatchDecoder` class implementing:
   - Patch Tokenizer: `tokenize_time_series(series, patch_size=3)`
   - Autoregressive Patch Forecast: `forecast_patches(history, horizon=6, patch_size=3)`
   - Quantile Distribution Estimation: `compute_quantiles(forecast_mean, std_err)`
   - Supplier Risk Index (SRI): `evaluate_supplier_risk(historical_series, forecasted_series)`
2. Build DB Extractor `get_supplier_timeseries_data(db_session, mst_supplier=None, tenant_id=None)` querying `InvoiceHeader` grouped by Seller MST and Month.

## Phase 2: REST Controllers (`invoices/routes/core.py`)
1. Register `GET /api/ai/timesfm/suppliers`: Lists top suppliers with total invoice count, tax sums, and risk score.
2. Register `POST /api/ai/timesfm/forecast`: Runs `TimesFMPatchDecoder` for target supplier.
3. Register `POST /api/ai/timesfm/scenario`: Performs counterfactual scenario simulations.

## Phase 3: Frontend Wise Bento Studio (`templates/tax_compliance_hub.html`)
1. Add **Module 5: Google TimesFM Studio - Supplier Tax & Fee Time-Series Forecasting**.
2. Add glassmorphic controls: Supplier Selector, Horizon Slider, Patch Size Selector, Scenario Adjustments.
3. Add JavaScript async handlers `loadTimesFMSuppliers()`, `runTimesFMForecast()`, `runTimesFMScenario()`.

## Phase 4: AI-Native Skill Package (`skills/timesfm-tax-forecaster/SKILL.md`)
1. Package instructions, rules, and examples into `.agents/skills/timesfm-tax-forecaster/SKILL.md`.

## Phase 5: Verification & Quality Gate
1. Create unit test suite `tests/test_timesfm_engine.py`.
2. Run pytest suite and verify 100% pass rate.
3. Record Telemetry Trace in `harness.db`.
