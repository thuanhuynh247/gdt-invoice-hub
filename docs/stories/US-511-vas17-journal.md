# Spec: US-511 — VAS 17 Deferred Tax Advisory Panel & Journal Entry Scaffolder

## Status

completed

## Lane

normal

## Product Contract

The system provides a journal entry generator for VAS 17 deferred tax changes (Tài khoản 243 / Tài khoản 347) paired with a compliance guidance summary that recommends specific adjustments based on Circular 45/2013/TT-BTC and Circular 48/2019/TT-BTC.

## Acceptance Criteria

- [x] Computes annual changes in Deferred Tax Assets and Deferred Tax Liabilities.
- [x] Generates double-entry journal suggestions:
  - Debit 243 / Credit 8212 (Deferred CIT tax asset increase)
  - Debit 8212 / Credit 243 (Deferred CIT tax asset decrease)
- [x] Renders a detailed double-entry advice table in the UI.
- [x] Links journal entries to tax regulations for audit defense reference.

## Validation

- `tests/test_v39_features.py::test_vas17_journal_entries`