# Spec: US-510 — Vietnamese Deferred Income Tax (VAS 17) Calculation Engine

## Status

completed

## Lane

normal

## Product Contract

The system implements a calculation engine for Vietnamese Deferred Income Tax in accordance with VAS 17. The engine computes temporary differences between accounting profit and taxable income arising from asset depreciation and provisions, determining deferred tax assets, liabilities, and double-entry adjustments.

## Acceptance Criteria

- [x] Database model or data structure to represent VAS 17 adjustments (e.g. temporary and permanent differences).
- [x] Logic to extract fixed asset depreciation entries and compute tax differences (accounting vs TT45 limits).
- [x] Logic to track disallowed provision limits (bad debts/inventory) and accrued expenses.
- [x] Computes net deferred tax asset (DTA) or deferred tax liability (DTL) positions at 20% CIT rate.

## Validation

- `tests/test_v39_features.py::test_vas17_deferred_tax_engine`