# Spec: US-652 — Interactive Version 53 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

Provides a premium web interface at `/v53-compliance-hub` with responsive calculators, audit trail logs, and a simulated AI/expert advisory debate panel focusing on green transition policies and EP tax rates. Also exposes JSON REST APIs for the calculators under `/api/v53/`.

## Acceptance Criteria

- [ ] Register `/v53-compliance-hub` route returning `templates/v53_compliance_hub.html`.
- [ ] Expose REST APIs under `/api/v53/`:
  - `GET /api/v53/compliance-data` - Returns latest logs for fuels, coal, plastic bags, and chemicals.
  - `POST /api/v53/fuel/calculate` - Calculate and log fuel EP tax.
  - `POST /api/v53/coal/calculate` - Calculate and log coal EP tax.
  - `POST /api/v53/bag/calculate` - Calculate and log plastic bag EP tax.
  - `POST /api/v53/chemical/calculate` - Calculate and log chemical EP tax.
- [ ] Incorporate dropdown navigation element in base layout for V53 Compliance Hub.
- [ ] Present responsive panels with premium look (glassmorphic styling, HSL tailormade palettes).
- [ ] Feature a simulated advisory debate panel with dynamic consensus summaries.

## Validation

- `tests/test_v53_features.py::test_api_routes_v53`
