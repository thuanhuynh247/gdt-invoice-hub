# Spec: US-485 — End-to-End CIT Finalization Validation Suite

## Status
planned

## Lane
normal

## Product Contract

The workspace contains an automated test suite verifying CIT finalization, optimal loss absorption offsets, GDT XML structures, and flask API routes.

## Acceptance Criteria

- [ ] Unit tests verify CIT tax calculations and GDT Form 03/TNDN formulas.
- [ ] Optimization tests check correct loss absorption behavior (expiry, maximum offset limits).
- [ ] Integration tests verify `/v36-cit-finalization` Flask view and API endpoints.
- [ ] Fully integrated into `tests/test_v36_features.py` and runs successfully.
