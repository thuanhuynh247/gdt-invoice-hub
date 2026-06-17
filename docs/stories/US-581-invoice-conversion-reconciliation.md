# Spec: US-581 — Circular 78 Legacy Conversions & Double-Deduction Auditing Engine

## Status

planned

## Lane

normal

## Product Contract

The system provides a conversion invoice auditing engine under Circular 78/2021/TT-BTC. It validates that converted paper copies of e-invoices meet compliance rules, and matches local purchases to prevent duplicate deductions of receipt and corresponding XML files.

## Acceptance Criteria

- [ ] Create `invoice_conversion_prints` and `conversion_reconciliation` tables in tenant databases.
- [ ] Implement conversion print counter limits to flag multiple prints of the same electronic invoice.
- [ ] Match legacy bills/tickets with corresponding XML e-invoices by date, seller MST, and amount.
- [ ] Raise warning flags (e.g. `DUPLICATE_CONVERSION_CLAIM`) if both conversion print and XML are claimed.

## Validation

- `tests/test_v46_features.py::test_conversion_reconciliation`
