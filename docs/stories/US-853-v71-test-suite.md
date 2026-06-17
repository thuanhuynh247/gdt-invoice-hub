# Story US-853: End-to-End V71 Verification Test Suite

## Business Need
Ensure the robustness, correctness, and regression protection of the Version 71 E-Waste compliance engine through automated testing.

## Technical Requirements
- Create pytest verification file `tests/test_v71_features.py`.
- Tests must cover:
  1. Core pricing rates for all product categories.
  2. Revenue and import threshold exemption rules.
  3. Export exclusions.
  4. Flask REST API routes (`/v71-compliance-hub`, `/api/v71/calculate`, `/api/v71/compliance-data`).
  5. Persistence of calculation history in tenant database.

## Acceptance Criteria
- Running `pytest tests/test_v71_features.py` must pass with zero failures.
