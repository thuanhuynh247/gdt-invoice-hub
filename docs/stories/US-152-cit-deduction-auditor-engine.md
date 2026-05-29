# US-152 CIT Deduction Auditor Engine

## Status

planned

## Lane

normal

## Product Contract

The application must include a Corporate Income Tax (CIT) deduction compliance engine that automatically flags invoices violating Vietnamese CIT deduction rules, including cash payments exceeding 20M VND, luxury vehicle purchases over 1.6B VND, and invoices from blacklisted/abandoned MSTs.

## Relevant Product Docs

- `docs/product/v12_roadmap.md`
- Thông tư 96/2015/TT-BTC (Circular 96/2015)

## Acceptance Criteria

- [ ] Implement rule engine scanning invoice attributes against CIT deduction thresholds.
- [ ] Flag invoices ≥ 20M VND paid in cash (payment_method = "TM/Cash") as non-deductible.
- [ ] Detect asset purchases exceeding statutory depreciation caps (passenger vehicles > 1.6B VND).
- [ ] Flag invoices from MSTs present on the GDT blacklist or marked as abandoned.
- [ ] Expose API endpoint `GET /api/tax/cit-audit` returning flagged items with rule citations.
- [ ] Write tests covering each flag rule with boundary value testing.

## Design Notes

- **Rule engine**: New function `run_cit_deduction_audit()` in `invoices/service.py`.
- **Threshold config**: Configurable via `SystemConfig` to accommodate regulation changes.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v12_cit_audit.py` with boundary tests (19.9M vs 20M cash, 1.59B vs 1.6B vehicle) |
| Integration | API returns correct flag categories and rule citations |
