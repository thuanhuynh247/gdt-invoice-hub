# Spec: US-640 — Sugary Beverages Roadmap & Air Conditioner Classifier Engine (Law 66)

## Status

planned

## Lane

normal

## Product Contract

The system classifies sugary beverages (>5g/100ml) and calculates SCT based on the 2026-2028 roadmap (excluding milk, fruit juices, etc.), and audits air conditioner capacities (24k to 90k BTU taxable at 10%, others exempt) under the Special Consumption Tax Law No. 66/2025/QH15.

## Acceptance Criteria

- [ ] Create `sugary_beverage_sct_logs` and `air_conditioner_sct_logs` tables in tenant databases.
- [ ] Evaluate sugary beverage sugar content. Apply SCT roadmap rates: 2026 = 0%, 2027 = 8%, 2028+ = 10%.
- [ ] Exclude milk, dairy, 100% fruit juice, coconut water, mineral water, and nectar from sugary beverage SCT.
- [ ] Validate air conditioner capacities. Apply 10% SCT to capacity > 24,000 BTU and <= 90,000 BTU. Flag capacity <= 24k BTU or > 90k BTU as EXEMPT.

## Validation

- `tests/test_v52_features.py::test_sugary_beverage_sct`
- `tests/test_v52_features.py::test_air_conditioner_sct`
