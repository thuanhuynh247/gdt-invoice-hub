# Spec: US-643 — End-to-End V52 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

The system provides a comprehensive verification suite validating all business rules, thresholds, exclusions, and APIs introduced in Version 52.0.0.

## Acceptance Criteria

- [ ] Create `tests/test_v52_features.py` testing sugary beverages roadmap calculations (2026/2027/2028), product exclusions, and BTU capacity checks.
- [ ] Test inland-to-nontariff area checks (including passenger car exclusions) and promotional equivalent pricing calculations.
- [ ] Test the `/v52-compliance-hub` endpoint and all dashboard API routes under a mock logged-in session.
- [ ] Ensure the tests can be successfully executed by the validation wrapper.

## Validation

- Pytest execution of `tests/test_v52_features.py`
