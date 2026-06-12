# US-693: End-to-End V57 Verification Test Suite

## Story
**As a** QA engineer,
**I want** a comprehensive pytest suite for the V57 Registration Fee engine,
**So that** all rate schedules, provincial surcharges, exemptions, and API endpoints are verified.

## Acceptance Criteria
- Tests cover real estate 0.5%, car 2%/12%, motorbike 2%/5%, yacht 1%.
- Tests cover all 4 exemption categories.
- Tests verify API POST /api/v57/calculate and GET /api/v57/compliance-data.
- Tests verify the compliance hub page renders with status 200.
- All tests pass via `pytest tests/test_v57_features.py`.
