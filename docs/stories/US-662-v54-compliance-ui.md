# Spec: US-662 — Interactive Version 54 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

Provides a premium web interface at `/v54-compliance-hub` with responsive NRT calculators for minerals, water, timber, and marine products, audit trail logs, and a simulated advisory debate panel. Also exposes JSON REST APIs under `/api/v54/`.

## Acceptance Criteria

- [ ] Register `/v54-compliance-hub` route returning `templates/v54_compliance_hub.html`.
- [ ] Expose REST APIs under `/api/v54/`:
  - `GET /api/v54/compliance-data` - Returns latest NRT calculation logs.
  - `POST /api/v54/mineral/calculate` - Calculate and log mineral NRT.
  - `POST /api/v54/water/calculate` - Calculate and log water resource NRT.
  - `POST /api/v54/timber/calculate` - Calculate and log timber NRT.
  - `POST /api/v54/marine/calculate` - Calculate and log marine product NRT.
- [ ] Incorporate dropdown navigation element in base layout for V54 Compliance Hub.
- [ ] Present responsive panels with premium look.
- [ ] Feature a simulated advisory debate panel.

## Validation

- `tests/test_v54_features.py::test_api_routes_v54`
