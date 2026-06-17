# Spec: US-631 — Cross-Border E-Commerce Vendor Tax & Withholding Tracker (Law 108)

## Status

completed

## Lane

normal

## Product Contract

The system tracks e-commerce MST registration statuses for foreign suppliers (e.g. Google, Netflix, Meta) and computes the withholding taxes (VAT + CIT) on B2B digital service purchases under Law 108/2025/QH15 rules.

## Acceptance Criteria

- [x] Create `foreign_vendor_registrations` and `ecommerce_withholding_logs` tables in tenant databases.
- [x] Determine if withholding is required (required if the foreign supplier is not registered on the GDT NTNN portal).
- [x] Calculate B2B withholding tax: 5% VAT on digital services, and CIT at 5% (services component) or 1% (goods component).
- [x] Log calculated tax amounts, foreign supplier MSTs, and transaction values.

## Validation

- `tests/test_v51_features.py::test_ecommerce_withholding_tax`
