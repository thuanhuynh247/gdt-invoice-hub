# Spec: US-661 — NRT Exemption & Threshold Auditor

## Status

planned

## Lane

normal

## Product Contract

Audit NRT exemptions for agricultural water, small-scale hydropower (≤ 2MW installed capacity), and self-consumed resources (70% rate reduction).

## Acceptance Criteria

- [ ] Exempt natural water used for agriculture, forestry, fishery, salt production (100%).
- [ ] Exempt hydropower stations with installed capacity ≤ 2MW (100%).
- [ ] Apply 70% rate for resources extracted and consumed internally by mining enterprises.
- [ ] Log exemption audit results to tenant-specific SQLite tables.

## Validation

- `tests/test_v54_features.py::test_water_nrt` (agricultural exemption cases)
- `tests/test_v54_features.py::test_mineral_nrt` (self-consumed resource cases)
