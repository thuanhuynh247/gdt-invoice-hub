# Spec: US-495 — End-to-End V37 Financial Intelligence Validation Suite

## Status
completed

## Lane
normal

## Product Contract

Provide comprehensive regression test coverage for all V37 features: CEO dashboard KPI aggregation and Health Score computation, multi-year tax projection accuracy with known datasets, tax calendar deadline calculations for edge cases, asset depreciation math (all 3 methods), TT45 compliance validation, and AI auto-linking accuracy with mock invoice data.

## Acceptance Criteria

- [x] All CEO Dashboard KPI aggregation formulas verified with controlled test data.
- [x] Financial Health Score computation validated across edge cases (all sub-scores at 0, 50, 100).
- [x] Tax projection regression accuracy verified against 12-month known dataset.
- [x] Calendar deadline calculations verified for leap years, weekends, and Vietnamese holidays.
- [x] Depreciation math verified for straight-line, declining balance, and production-based methods.
- [x] TT45 Appendix 1 maximum useful life limits enforced in validation tests.
- [x] AI auto-linking tested with mock invoices (asset and non-asset) for precision/recall.
- [x] All tests pass via `python scripts/harness_win.py validate --cmd "venv\\Scripts\\python.exe -m pytest tests/test_v37_features.py"`.

## Validation

- `tests/test_v37_features.py` (full suite)
