# Spec: US-531 — Export Customs-to-Invoice Matcher

## Status

planned

## Lane

normal

## Product Contract

The system reconciles export customs declarations with corresponding GTGT export invoices. It verifies:
- Match of seller MST and buyer name/ID.
- Match of export values (allowing a small tolerance under 0.5% for currency exchange rate differences).
- Match of key items and quantities.
- Check that the clearance date is within the legal tax declaration timeline.

## Acceptance Criteria

- [ ] Implement `DeclarationInvoiceMatch` model in database to record match state and discrepancies.
- [ ] Add a service method to perform automatic matching and flag unmatched or value-mismatched records.
- [ ] Render matching status in the UI (e.g. matched, value mismatch, unmatched).

## Validation

- `tests/test_v41_features.py::test_customs_invoice_matcher`
