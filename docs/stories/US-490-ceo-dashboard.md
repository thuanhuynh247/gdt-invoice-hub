# Spec: US-490 — CEO Executive KPI Dashboard & Financial Health Score

## Status
completed

## Lane
normal

## Product Contract

The system provides a **CEO Executive Command Center** at `/v37-ceo-dashboard` with glassmorphic styling, aggregating Revenue, Expense, Tax Liability, Cash Flow, Audit Risk metrics, and a Financial Health Score (0-100). Includes an interactive Sankey SVG diagram (Revenue → COGS → Gross Profit → OpEx → Tax → Net Income), AI-generated management commentary in Vietnamese, and a Board Report PDF/PPTX export.

## Acceptance Criteria

- [x] Web view `/v37-ceo-dashboard` is accessible with responsive glassmorphic layout.
- [x] Displays aggregated KPI cards: Total Revenue, Total Expense, Net Profit, Tax Liability, Cash Runway.
- [x] Computes Financial Health Score (0-100) from Cash, Tax Compliance, Audit Risk, and AR Aging sub-scores.
- [x] Renders interactive Sankey SVG diagram showing financial flows.
- [x] Supports QoQ/YoY comparative analysis with anomaly highlighting.
- [x] AI generates Vietnamese management narrative from structured KPI data.
- [x] Board Report exportable as PDF.

## Validation

- `tests/test_v37_features.py::test_ceo_dashboard_health_score`
- `tests/test_v37_features.py::test_ceo_dashboard_kpi_aggregation`
- `tests/test_v37_features.py::test_sankey_data_generation`
