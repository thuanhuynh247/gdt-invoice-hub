# Spec: US-555 — End-to-End V43 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

A comprehensive test suite verifying the correctness of the IFRS & International Tax Engine calculations, endpoints, database persistence, and UI routes.

## Acceptance Criteria

- [ ] Create pytest file `tests/test_v43_features.py`.
- [ ] Test IAS 12 deferred tax calculations, asserting correct DTA/DTL results.
- [ ] Test IFRS 15 allocation and recognition matching logic.
- [ ] Test IFRS 16 amortization PV and schedule calculation.
- [ ] Test OECD Pillar Two ETR calculations and top-up tax estimations.
- [ ] Test the integration endpoints and UI page routes under simulated user sessions.

## Validation

- Pytest execution: `pytest tests/test_v43_features.py` must run and pass all test cases.
