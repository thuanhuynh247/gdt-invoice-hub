# Spec: US-663 — End-to-End V54 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

Verifies correct NRT rates for minerals, water, timber, and marine products, agricultural exemptions, hydropower threshold checks, self-consumed resource rate adjustments, dashboard view rendering, and REST JSON API endpoints using pytest.

## Acceptance Criteria

- [ ] Test mineral NRT rates (iron, copper, gold, tin, granite, sand, marble, limestone).
- [ ] Test water NRT with agricultural exemption (100%) and hydropower exemption (≤ 2MW).
- [ ] Test timber NRT for natural forest vs. plantation.
- [ ] Test marine NRT for aquatic products vs. pearls/coral.
- [ ] Test self-consumed resource 70% rate reduction.
- [ ] Test HTTP API status codes, view rendering, and REST response shapes.

## Validation

- Pytest runs and all tests pass.
