# Spec: US-612 — Interactive Version 49 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

The system provides a web dashboard at `/v49-compliance-hub` and backend REST API endpoints to simulate SME progressive CIT rates, calculate real estate loss carry-overs, audit foreign digital platforms withholdings, and verify green bond / carbon credit exemptions.

## Acceptance Criteria

- [ ] Register routes `/v49-compliance-hub` and API endpoints `/api/v49/compliance-data`, `/api/v49/sme-cit/calculate`, and `/api/v49/re-loss/offset`.
- [ ] Implement an interactive dashboard page displaying threshold alerts, CIT calculations, and exemption logs.
- [ ] Ensure full integration with the application layout and navigation bar.

## Validation

- `tests/test_v49_features.py::test_v49_compliance_hub_routes`
