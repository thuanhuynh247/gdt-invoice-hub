# Spec: US-554 — Interactive IFRS Translation & OECD GMT Compliance Dashboard UI

## Status

planned

## Lane

normal

## Product Contract

An interactive, premium dashboard page accessible at `/v43-ifrs-dashboard` that visualizes the IFRS translation layer adjustments, lease schedules, and consolidated global minimum tax projections.

## Acceptance Criteria

- [ ] Route `/v43-ifrs-dashboard` served via invoices blueprint.
- [ ] Bento Grid design displaying cards for IAS 12 Deferred Tax, IFRS 15 Revenue, IFRS 16 Leases, and OECD Pillar Two GMT.
- [ ] Interactive sliders for modifying simulation parameters (lease monthly payment, lease discount rate, global minimum tax rate).
- [ ] Visual maps or graphs representing group ETR status across MST nodes, with highlights for those below 15%.
- [ ] AI Swarm debate panel to get consensus on complex translation treatments.

## Validation

- `tests/test_v43_features.py::test_dashboard_routes`
