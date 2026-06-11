# Spec: US-552 — IFRS 16 Lease Amortization Matcher & ROU schedule generator

## Status

planned

## Lane

normal

## Product Contract

The system automates lease amortization schedules and Right-of-Use (ROU) asset/liability management under IFRS 16, computing present values and separating interest and principal payments month-by-month.

## Acceptance Criteria

- [ ] Support `lease_amortization_schedule` table in the tenant database.
- [ ] Implement present value calculation of future lease payments as the opening balance of ROU Asset / Lease Liability.
- [ ] Generate a monthly amortization schedule tracking interest expense (using periodic rate) and principal repayments, reducing liability balance to zero.

## Validation

- `tests/test_v43_features.py::test_ifrs16_lease_amortization`
