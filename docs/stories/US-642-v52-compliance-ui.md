# Spec: US-642 — Interactive Version 52 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

The system provides an interactive dashboard UI at `/v52-compliance-hub` and supporting REST APIs to compute, simulate, and audit SCT compliance for Law 66/2025/QH15.

## Acceptance Criteria

- [ ] Create `/v52-compliance-hub` Flask route rendering `v52_compliance_hub.html`.
- [ ] Implement REST APIs under `/api/v52/` for sugary beverage calculation, air conditioner classification, non-tariff area audits, and promotional price adjustments.
- [ ] Include interactive simulation calculators for each pillar on the dashboard UI.
- [ ] Add the mock consensus debate panel containing transcripts between auditors, tax managers, and advisors regarding Law 66 implementation details.

## Validation

- `tests/test_v52_features.py::test_v52_api_routes_and_ui`
