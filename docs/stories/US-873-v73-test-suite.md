# Story US-873: End-to-End V73 Verification Test Suite

## Business Need
Ensure the robustness, correctness, and regression protection of the Version 73 hazardous waste compliance engine through automated testing.

## Technical Requirements
- Create pytest verification file `tests/test_v73_features.py`.
- Tests must cover:
  1. Base licensing application fee.
  2. Disposal surcharges for Category A and Category B waste.
  3. Small generator threshold exemption (< 600 kg/year).
  4. Academic/research lab exemptions.
  5. Flask REST API routes (`/v73-compliance-hub`, `/api/v73/calculate`, `/api/v73/compliance-data`).
  6. Persistence of hazardous waste logs.

## Acceptance Criteria
- Running `pytest tests/test_v73_features.py` must pass with zero failures.
