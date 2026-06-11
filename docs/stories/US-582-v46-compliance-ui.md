# Spec: US-582 — Interactive Version 46 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

Exposes REST API endpoints and a web console at `/v46-compliance-hub` to track Form 04/SS-HĐĐT statuses, conversion audits, and warning analytics.

## Acceptance Criteria

- [ ] Register `/v46-compliance-hub` page route and API endpoints `/api/v46/compliance-data`, `/api/v46/incidents/submit-form`, and `/api/v46/conversions/reconcile`.
- [ ] Render incident trackers, status timelines, and conversion warning alerts.
- [ ] Ingest mock GDT responses via API simulation endpoints.
- [ ] Display an advisory debate panel simulating audit risks and solutions.

## Validation

- `tests/test_v46_features.py::test_v46_api_routes`
