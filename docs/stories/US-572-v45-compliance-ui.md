# Spec: US-572 — Interactive Version 45 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

The system exposes REST API endpoints and a web console at `/v45-compliance-hub` showcasing CIT preferential rates, tax holidays, and TP Safe Harbor compliance. The UI includes input sliders and interactive widgets to simulate tax optimization scenarios.

## Acceptance Criteria

- [ ] Register routes `/v45-compliance-hub` and API endpoints `/api/v45/compliance-data`, `/api/v45/cit-incentives/calculate`, and `/api/v45/tp-safe-harbors/evaluate`.
- [ ] Implement input sliders on UI for taxable income segmentation, revenue, and margins.
- [ ] Render interactive charts/widgets displaying CIT savings and Safe Harbor status.
- [ ] Display an advisory debate panel simulating tax inspectors and CFO consultancies.

## Validation

- `tests/test_v45_features.py::test_v45_api_routes`
