# US-191 Customs-to-Invoice Matcher & Discrepancy Detector

## Status

planned

## Lane

normal

## Product Contract

The application must provide a reconciliation tool that matches customs declarations against domestic purchase/sale invoices and payment vouchers, flagging tax discrepancies, value mismatches, and missing documents.

## Relevant Product Docs

- `docs/product/v16_roadmap.md`

## Acceptance Criteria

- [ ] Create a reconciliation database model linking Customs Declarations to domestic Invoices.
- [ ] Implement matching algorithms checking declaration IDs, payment vouchers, total values, and tax codes.
- [ ] Build a reconciliation comparison UI highlight discrepancies (e.g., mismatch in VAT paid, missing invoice).
- [ ] Support exporting matched and unmatched lists to Excel/CSV for accounting records.
- [ ] Expose API endpoint `GET /api/customs/reconcile` to perform analysis and retrieve mismatch items.
- [ ] Write unit tests verifying matching logic and discrepancy flags.

## Design Notes

- **Module**: `invoices/customs_matcher.py`
- **Reconciliation Storage**: Persists match records in database table `CustomsReconciliation`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v16_customs_matcher.py` testing matcher logic, discrepancy flags, and edge cases |
| Integration | Calling `/api/customs/reconcile` returns matched lists and correctly alerts value differences |
