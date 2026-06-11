# Spec: US-542 — E-Commerce Transaction Matcher & Circular 80 Withholding Auditor

## Status

planned

## Lane

normal

## Product Contract

The system reconciles platform transaction logs with issued sales invoices, detects revenue gaps, and audits platform tax withholding compliance (VAT 1%, PIT 0.5%) under Circular 80/2021/TT-BTC.

## Acceptance Criteria

- [ ] Implement `ECommercePlatformTransaction` and `ECommerceReconciliationReport` models in `invoices/models.py`.
- [ ] Create E-Commerce matching logic in `invoices/v42_service.py` to:
  - Match platform records with sales invoices by date, buyer, and amount (within 1% tolerance).
  - Calculate platform revenue, invoiced revenue, and gap amounts.
  - Audit withholding compliance (flag if the platform did not withhold VAT 1% or PIT 0.5% for individual sellers, or check corporate credentials).
- [ ] Return a comprehensive reconciliation report dict.

## Validation

- `tests/test_v42_features.py::test_ecommerce_transaction_reconciler`
