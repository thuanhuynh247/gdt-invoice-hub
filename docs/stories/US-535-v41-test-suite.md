# Spec: US-535 — End-to-End V41 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

The system contains comprehensive unit, integration, and E2E regression tests verifying customs declaration parsing, invoice reconciliation matching, Form 01-1/GTGT and Form 01/ĐNHT calculations, and dashboard rendering.

## Acceptance Criteria

- [ ] Implement Pytest test suite covering all services in `invoices/v41_service.py`.
- [ ] Verify XML parser correctly extracts fields and handles errors.
- [ ] Test the matching logic with tolerances and legal time limit alerts.
- [ ] Verify correct math for tax refund request limits.
- [ ] Verify API routes return status 200 for authenticated requests.

## Validation

- `tests/test_v41_features.py`
