# US-160 Tax Deadline Alerter

## Status

implemented

## Lane

normal

## Product Contract

The application must proactively calculate and display upcoming Vietnamese tax filing deadlines (quarterly VAT, quarterly CIT provisional, annual CIT final) with configurable advance-warning countdown badges on the dashboard.

## Relevant Product Docs

- `docs/product/v13_roadmap.md`
- Nghị định 125/2020/NĐ-CP (Penalty for late filing)

## Acceptance Criteria

- [x] Implement deadline calculation engine based on Vietnamese fiscal calendar rules.
- [x] Display countdown badges on dashboard (30-day green, 15-day yellow, 7-day orange, overdue red).
- [x] Expose API `GET /api/notifications/deadlines` returning next upcoming deadlines.
- [x] Support configurable advance-warning thresholds via SystemConfig.
- [x] Write tests verifying deadline calculation accuracy across quarter boundaries.

## Design Notes

- **Module**: New functions in `invoices/service.py`.
- **Calendar rules**: Q1 deadline = Apr 30, Q2 = Jul 31, Q3 = Oct 31, Q4 = Jan 31 next year. CIT annual = Mar 31.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v13_deadline_alerter.py` with mocked dates |
| Integration | API returns correct deadlines relative to current date |
