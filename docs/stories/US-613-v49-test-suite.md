# Spec: US-613 — End-to-End V49 Verification Test Suite

## Status

completed

## Lane

normal

## Product Contract

The system provides an automated end-to-end verification test suite to ensure the accuracy of the SME progressive rate classifier, the real estate loss offset calculations, the foreign provider CIT withholdings, the green tax exemptions, and the REST routes.

## Acceptance Criteria

- [x] Write integration and end-to-end unit tests in `tests/test_v49_features.py`.
- [x] Verify database state changes and transaction logs after auditing.
- [x] Test positive and negative boundaries for revenue thresholds (3B and 50B VND).
- [x] Ensure execution through the harness validation wrapper.

## Validation

- `tests/test_v49_features.py`
