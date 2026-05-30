# US-180 CIT Calculation & Form 03/TNDN Scaffolder

## Status

planned

## Lane

normal

## Product Contract

The system must automatically aggregate financial data (revenue, cost of goods sold, deductible/non-deductible expenses, and related-party interest caps) from the local database, calculate Corporate Income Tax (CIT) liability, and scaffold the statutory Form 03/TNDN (Tờ khai quyết toán thuế TNDN) in HTKK-compatible XML and Excel format.

## Relevant Product Docs

- `docs/product/v15_roadmap.md`
- Nghị định 132/2020/NĐ-CP (Transfer pricing related-party interest cap of 30% EBITDA)
- Thông tư 80/2021/TT-BTC (Guidelines on tax administration and declaration forms)

## Acceptance Criteria

- [ ] Aggregates financial items (revenue, costs, interest expenses) from invoices and profiles.
- [ ] Automatically computes and applies the 30% EBITDA loan interest cap under Decree 132/2020/NĐ-CP.
- [ ] Supports manual line-item adjustments for non-deductible cost inputs (e.g., welfare exceedances).
- [ ] Generates the statutory XML schema and Excel structure for Form 03/TNDN compatible with GDT's HTKK software.
- [ ] Exposes API endpoint `POST /api/cit/finalize` to trigger report generation.
- [ ] Write unit tests verifying CIT calculations, EBITDA interest caps, and XML generation validity.

## Design Notes

- **Module**: `invoices/cit_engine.py`
- **Output XML Format**: Standard HTKK Form 03/TNDN schema structure.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v15_cit_engine.py` checking CIT calculation correctness and interest expense deductions |
| Integration | API endpoint `POST /api/cit/finalize` successfully queries database and returns HTKK-compliant XML payload |
