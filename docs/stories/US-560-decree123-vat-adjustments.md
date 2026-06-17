# Spec: US-560 — Decree 123 VAT Adjustment & Returned Goods Reconciliation Engine

## Status

planned

## Lane

normal

## Product Contract

The system provides an auditing and reconciliation engine for VAT adjustment invoices, replacement invoices, and trade discounts under Decree 123/2020/NĐ-CP. It validates adjustment invoices against their original sales/purchase invoices to ensure tax compliance, preventing disallowed VAT deductions and CIT audit exposures.

## Acceptance Criteria

- [ ] Create `decree123_invoice_adjustments` table inside isolated tenant database.
- [ ] Match adjustment/replacement/discount invoices against original sales/purchase invoices by original invoice symbol/number.
- [ ] Implement validation audit rules:
  - The sum of adjustment amounts (positive or negative) must not exceed the original invoice's net amount or VAT amount.
  - Buyer and seller taxpayer MSTs must match the original invoice.
  - The tax rate (VAT) must match the adjusted line item's original tax rate.
  - Flag any adjustment without a valid original invoice reference as "Unlinked".
- [ ] Expose reconciliation service functions and save the audit results.

## Validation

- `tests/test_v44_features.py::test_decree123_vat_adjustments`
