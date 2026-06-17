# Spec: US-460 — Invoice Aging Analysis & Accounts Receivable/Payable Engine

## Status
implemented

## Lane
normal

## Product Contract

The system provides an **Invoice Aging Analysis Engine** that classifies invoices into aging buckets (Current, 1-30 days, 31-60 days, 61-90 days, 90+ days overdue) for both Accounts Receivable (output invoices) and Accounts Payable (input invoices). Enables proactive debt management and cash flow optimization.

## Acceptance Criteria

- [x] `invoices/v34_service.py` provides `analyze_invoice_aging(taxpayer_mst, as_of_date)` returning AR/AP aging breakdown.
- [x] Aging buckets: Current, 1-30, 31-60, 61-90, 90+ days with invoice counts and amounts.
- [x] `generate_aging_heatmap_data(aging_result)` returns structured data for SVG heatmap rendering.
- [x] AI Swarm advisory for debt collection strategy.
- [x] API endpoints for aging analysis, heatmap data, and swarm chat.
- [x] Full test coverage in `tests/test_v34_features.py`.
