# US-150 Smart Cash Flow Predictor

## Status

implemented

## Lane

normal

## Product Contract

The application must project rolling 30/60/90-day cash availability by combining pending invoice receivables, payables, and projected VAT liabilities into a unified cash-flow timeline. Results are exposed via a dedicated API and rendered as an interactive SVG chart on the dashboard.

## Relevant Product Docs

- `docs/product/v12_roadmap.md`

## Acceptance Criteria

- [x] Implement calculation engine aggregating invoice due dates, amounts receivable/payable, and forecasted VAT obligations.
- [x] Expose API endpoint `GET /api/finance/cashflow` returning rolling projection datasets (30/60/90 days).
- [x] Render an interactive SVG line chart on the dashboard showing projected cash balance over time.
- [x] Write unit tests verifying projection accuracy against known invoice datasets.

## Design Notes

- **Calculation module**: `invoices/service.py` — new function `calculate_cashflow_projection()`.
- **API route**: `/api/finance/cashflow` in `invoices/routes.py`.
- **Chart**: Dynamic SVG generated client-side from API response data.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v12_cashflow.py` verifies rolling aggregation accuracy |
| Integration | API returns correct JSON structure with projection arrays |
