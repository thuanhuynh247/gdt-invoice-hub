# US-175 Foreign Contractor Tax Compliance Auditor

## Status

planned

## Lane

normal

## Product Contract

The application must audit invoices from cross-border service providers (such as Google, Meta, AWS), compute Foreign Contractor Tax (FCT) VAT and CIT liability, and track withholding payment deadlines.

## Relevant Product Docs

- `docs/product/v14_roadmap.md`
- Circular 103/2014/TT-BTC (Vietnamese Foreign Contractor Tax regulations)

## Acceptance Criteria

- [ ] Detect cross-border service transactions using supplier country or specialized FCT tags.
- [ ] Calculate FCT liabilities (VAT and CIT withholding portions) based on standard tax rates (e.g. 5% VAT, 5% CIT for services).
- [ ] Display an FCT audit dashboard showing tax due dates and withholding liabilities.
- [ ] Support exporting monthly/quarterly FCT tax declaration worksheets to Excel.
- [ ] Write tests validating FCT withholding calculations for gross-up and net-contract types.

## Design Notes

- **Module**: `invoices/fct_auditor.py`.
- **FCT rates**: Services: VAT 5%, CIT 5%. Software/Royalties: VAT exempt, CIT 10%.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v14_fct_auditor.py` checking net and gross rate withholding math |
| Integration | FCT declaration worksheets export files with correct aggregated numbers |
