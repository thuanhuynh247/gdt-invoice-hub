# Spec: US-573 — End-to-End V45 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

An isolated automated test suite verifying CIT preferential rate distributions, tax holidays, related-party Safe Harbor assessments, and dashboard API responses.

## Acceptance Criteria

- [ ] Write a pytest suite in `tests/test_v45_features.py`.
- [ ] Test the database schema initialization in tenant databases.
- [ ] Test Preferential CIT rate calculations and holiday exemptions.
- [ ] Test Safe Harbor rules and APA margin tracking.
- [ ] Test API endpoints `/api/v45/compliance-data` and simulation routes.

## Validation

- `tests/test_v45_features.py`
