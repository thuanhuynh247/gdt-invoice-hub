# Spec: US-621 — Wage progressive brackets scheduler & Family Deduction Engine (Law 109, Article 7)

## Status

planned

## Lane

normal

## Product Contract

The system implements the progressive PIT brackets calculation (5% to 35%) and monthly family deductions (15M VND for personal, 5.5M VND per dependent) for salary and wage earners under the amended Article 7 of Law 109/2025/QH15.

## Acceptance Criteria

- [ ] Create `salary_pit_deductions` and `progressive_pit_ledgers` tables in tenant databases.
- [ ] Implement personal deduction of 15,000,000 VND/month and dependent deduction of 5,500,000 VND/month per dependent.
- [ ] Build the 7-grade progressive tax bracket calculator based on taxable income.
- [ ] Log deductions and final PIT calculated in the tenant database ledger.

## Validation

- `tests/test_v50_features.py::test_wage_pit_bracket_and_deductions`
