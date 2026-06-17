# Spec: US-551 — IFRS 15 Revenue Recognition & Contract Milestone Matcher

## Status

planned

## Lane

normal

## Product Contract

The system manages revenue recognition under IFRS 15. It handles performance obligations (performance obligation matching), allocates contract transaction prices based on relative standalone selling prices (SSP), and defers/recognizes revenue based on satisfied milestones.

## Acceptance Criteria

- [ ] Support `ifrs15_revenue_contracts` and `ifrs15_performance_obligations` tables in the tenant database.
- [ ] Implement price allocation engine that splits contract transaction price proportionally based on relative Standalone Selling Price (SSP).
- [ ] Implement milestone matching that updates recognized and deferred revenue upon obligation satisfaction.

## Validation

- `tests/test_v43_features.py::test_ifrs15_revenue_allocation_and_recognition`
