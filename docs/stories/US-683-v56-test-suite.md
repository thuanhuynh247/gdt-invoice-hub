# US-683: End-to-End V56 Verification Test Suite

## Description
As a QA engineer, I want to execute automated tests verifying License Fee calculations, brackets, branch rules, first-year exemptions, and JSON APIs so that I can prevent regressions.

## Acceptance Criteria
- Create `tests/test_v56_features.py` with pytest test cases.
- Verify enterprise brackets, household revenue brackets, newly established exemptions, and agricultural cooperative exemptions.
- Verify route `/v56-compliance-hub` and REST endpoints.
- Execute clean tenant db bootstrap during tests.
