# Spec: US-440 — Input Invoice Supplier Monthly Pivot Summary Engine

## Status
implemented

## Lane
high_risk

## Acceptance Criteria
- **Endpoint**: `GET /api/invoices/supplier-pivot`
- **Authentication**: Gated by `_ensure_logged_in()`.
- **Query Params**:
  - `year`: Selected calendar year (e.g. `2026`). If empty, compute dynamic month columns for all years (e.g. `2025-01`, `2026-12`).
  - `value_type`: Column metrics to sum/calculate. Values: `total_amount` (default), `amount_before_tax`, `tax_amount`, `invoice_count`.
- **Filtering**:
  - Only input invoices (`invoice_type = 'purchase'`).
  - Filter by tenant taxpayer MST (`active_taxpayer_mst` from session/parameters).
- **Output JSON Schema**:
  - Contains `success` (boolean), `year`, `value_type`.
  - `months`: List of columns/months shown (e.g. `["01", "02", ..., "12"]` for single year, or chronological `["2025-01", "2026-05"]` for all years).
  - `rows`: List of supplier records, each with `seller_mst`, `seller_name`, `monthly_values` (dictionary of month -> sum), and `row_total` (sum of that supplier).
  - `column_totals`: Dictionary of month -> sum of all suppliers for that month.
  - `grand_total`: Grand total of all values.
