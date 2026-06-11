# Spec: US-561 — Circular 67 & Circular 05 Science & Technology Development Fund Optimizer

## Status

planned

## Lane

normal

## Product Contract

The system implements a simulator and optimizer for the Science and Technology Development Fund (Circular 67/2022/TT-BTC & Circular 05/2022/TT-BKHCN). It calculates the tax-deductible fund allocation ceiling, tracks R&D expenditures, and simulates CIT clawback plus 0.03% daily late payment interest for unspent funds after the 5-year statutory period. It also incorporates the corporate welfare fund CIT ceiling (1-month average salary).

## Acceptance Criteria

- [ ] Create `sci_tech_fund_ledger` and `sci_tech_expenditures` tables in the tenant database.
- [ ] Implement fund optimization calculations:
  - Max CIT taxable income deduction allocation (up to 10% of profit).
  - Simulate the 5-year timeline from allocation year, tracking qualified expenditures vs non-qualified expenditures.
  - Calculate CIT clawback amount (taxable portion of unspent fund multiplied by statutory CIT rate).
  - Simulate daily late payment interest (lãi chậm nộp) at 0.03% per day from the allocation year's tax filing deadline.
  - Compute Corporate Welfare Fund CIT ceiling limit based on 1-month average salary of the year.

## Validation

- `tests/test_v44_features.py::test_circular67_sci_tech_fund`
