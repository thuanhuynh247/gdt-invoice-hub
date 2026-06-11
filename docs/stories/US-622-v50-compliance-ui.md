# Spec: US-622 — Interactive Version 50 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

The system provides a web dashboard at `/v50-compliance-hub` and backend REST API endpoints to simulate wage progressive PIT calculations, verify personal/dependent deductions, and audit household businesses tax liabilities under the Law 109/2025/QH15 rules.

## Acceptance Criteria

- [ ] Register routes `/v50-compliance-hub` and API endpoints `/api/v50/compliance-data`, `/api/v50/wage-pit/calculate`, and `/api/v50/household-pit/evaluate`.
- [ ] Implement an interactive dashboard page displaying family deductions configuration, wage sliders, and tax audit tables.
- [ ] Ensure full integration with the application layout and navigation bar.

## Validation

- `tests/test_v50_features.py::test_v50_compliance_hub_routes`
