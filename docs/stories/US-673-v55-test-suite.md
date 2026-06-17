# US-673: End-to-End V55 Verification Test Suite

## Description
As a QA engineer, I want to execute automated tests verifying Import-Export calculations, exemptions, routes, and JSON APIs so that I can prevent regressions.

## Acceptance Criteria
- Create `tests/test_v55_features.py` with pytest test cases.
- Verify standard ordinary and MFN rates, processing contract exemptions, and low-value gift thresholds.
- Verify route `/v55-compliance-hub` and REST endpoints.
- Execute clean tenant db bootstrap during tests.
