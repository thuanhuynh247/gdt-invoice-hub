# Spec: US-570 — Circular 80 Preferential CIT Rates & Tax Holidays Optimizer

## Status

completed

## Lane

normal

## Product Contract

The system provides an optimization and calculation engine for corporate tax incentives under Circular 80/2021/TT-BTC. It segregates corporate income, applies preferential tax rates (10%, 15%, 17% instead of the standard 20%), and allocates tax exemption/reduction holidays to minimize corporate CIT liabilities.

## Acceptance Criteria

- [x] Create `cit_preferential_ledger` table inside isolated tenant database.
- [x] Implement income segregation logic to split taxable income between preferential projects and standard operations.
- [x] Calculate CIT liabilities with preferential tax rates (10%, 15%, 17%).
- [x] Apply tax holidays exemptions (100% reduction) and reductions (50% reduction) based on holiday duration and timeline.
- [x] Compute the net CIT savings and overall tax liability projection.

## Validation

- `tests/test_v45_features.py::test_preferential_cit_rates`
