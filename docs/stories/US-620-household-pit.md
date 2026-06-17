# Spec: US-620 — Household Business PIT Exemption & Revenue Tracker (Law 109)

## Status

planned

## Lane

normal

## Product Contract

The system audits household business revenue records against the new 500M VND non-taxable threshold, determines their PIT exemption status, and applies proper PIT rates (0.5% - 2.0%) based on activity types for revenue exceeding the threshold under PIT Law 109/2025/QH15.

## Acceptance Criteria

- [ ] Create `household_pit_exemptions` and `household_pit_audit_log` tables in tenant databases.
- [ ] Implement the 500M VND annual revenue threshold check. Exclude qualifying businesses with revenue ≤ 500M VND from PIT liability.
- [ ] For revenue > 500M VND, apply correct PIT rates by business activity: distribution/retail (0.5%), services/construction (2.0%), manufacturing/transport (1.5%), other (1.0%).
- [ ] Log status and computed PIT liabilities in the tenant ledger.

## Validation

- `tests/test_v50_features.py::test_household_pit_evaluation`
