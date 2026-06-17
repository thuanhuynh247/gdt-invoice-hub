# Spec: US-491 — Multi-Year Tax Projection Engine & Optimization Simulator

## Status
completed

## Lane
normal

## Product Contract

The system provides a **Multi-Year Tax Projection Engine** that forecasts VAT, CIT, PIT, and FCT obligations 3-5 years ahead using historical invoice data, linear regression trends, and user-defined growth assumptions. Includes an NPV Optimizer comparing tax strategies (CIT incentive timing, loss carry-forward deferral, VAT refund timing) and a scenario comparison dashboard (Best/Base/Worst case).

## Acceptance Criteria

- [x] API endpoint `/api/tax-planning/projection` returns year-by-year tax forecast for VAT, CIT, PIT, FCT.
- [x] Supports user-configurable growth rate (%) and cost inflation rate (%).
- [x] Computes 3 scenarios (Best/Base/Worst) with ±20% variance.
- [x] NPV optimizer calculates tax savings across strategies at configurable discount rate.
- [x] SVG line chart visualizing projected tax obligations across years.
- [x] Comparison table showing NPV of each strategy with recommended choice.

## Validation

- `tests/test_v37_features.py::test_tax_projection_linear_regression`
- `tests/test_v37_features.py::test_tax_projection_scenarios`
- `tests/test_v37_features.py::test_npv_optimizer_strategies`
