# Intent: Google TimesFM Supplier Tax & Fee Time-Series Forecasting Engine

## Stable Identifiers
- **Problem ID**: `[PRB-111]`
- **Output ID**: `[OUT-111]`
- **Feature ID**: `[FR-111]`

## Business Need
Finance and tax teams currently lack granular, zero-shot predictive visibility into supplier-level (NCC - Nhà Cung Cấp) tax liabilities, VAT input projections, and Foreign Contractor Tax (FCT/WHT) obligations. Standard linear trend models fail to capture complex seasonal patterns, sudden supplier tax spikes, and multi-horizon risk bounds.

## Objectives
1. Adapt Google Research's **TimesFM** (Time Series Foundation Model) patch-decoder architecture for zero-shot time-series forecasting on supplier tax data.
2. Tokenize supplier invoice transactions into patch representations (e.g. 3-month / 6-month patches).
3. Generate point forecasts (P50) and multi-quantile risk bounds (P10, P25, P75, P90, P95) for 1 to 12 months ahead.
4. Detect abnormal supplier tax spikes and risk anomalies (Supplier Risk Index).
5. Build an interactive Wise Bento Studio UI (`tax_compliance_hub.html`) for running TimesFM forecasts and counterfactual scenarios.
