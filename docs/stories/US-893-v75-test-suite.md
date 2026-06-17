# Story US-893: End-to-End V75 Verification Test Suite

## Business Need
Ensure the robustness, correctness, and regression protection of the Version 75 plastics levy compliance engine through automated testing.

## Technical Requirements
- Create pytest verification file `tests/test_v75_features.py`.
- Tests must cover:
  1. Base rates for plastic bags, cups/straws, and EPS boxes.
  2. Biodegradable plastic, export packaging, and agricultural mulching film exemptions.
  3. Flask REST API routes (`/v75-compliance-hub`, `/api/v75/calculate`, `/api/v75/compliance-data`).
  4. Persistence of plastic levy logs.

## Acceptance Criteria
- Running `pytest tests/test_v75_features.py` must pass with zero failures.
