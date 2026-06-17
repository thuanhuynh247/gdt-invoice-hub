# Spec: US-663 — End-to-End V54 Verification Test Suite

## Status

completed

## Lane

normal

## Product Contract

Verifies correct NRT rates for minerals, water, timber, and marine products, agricultural exemptions, hydropower threshold checks, self-consumed resource rate adjustments, dashboard view rendering, and REST JSON API endpoints using pytest.

## Acceptance Criteria

- [x] Test mineral NRT rates (iron, copper, gold, tin, granite, sand, marble, limestone).
- [x] Test water NRT with agricultural exemption (100%) and hydropower exemption (≤ 2MW).
- [x] Test timber NRT for natural forest vs. plantation.
- [x] Test marine NRT for aquatic products vs. pearls/coral.
- [x] Test self-consumed resource 70% rate reduction.
- [x] Test HTTP API status codes, view rendering, and REST response shapes.

## Validation

- Pytest runs and all tests pass.
