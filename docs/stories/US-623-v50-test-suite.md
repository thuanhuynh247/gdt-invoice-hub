# Spec: US-623 — End-to-End V50 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

The system provides an automated end-to-end verification test suite to ensure the accuracy of the household business PIT exemption tracker, the salary progressive brackets, the personal/dependent deductions, and the web routes.

## Acceptance Criteria

- [ ] Write integration and end-to-end unit tests in `tests/test_v50_features.py`.
- [ ] Verify database state changes and transaction logs after auditing.
- [ ] Test boundaries of family deductions and household PIT thresholds.
- [ ] Ensure execution through the harness validation wrapper.

## Validation

- `tests/test_v50_features.py`
