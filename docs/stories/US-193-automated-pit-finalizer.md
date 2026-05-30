# US-193 Automated PIT Finalizer & Form 05/QTT-TNCN Scaffolder

## Status

planned

## Lane

normal

## Product Contract

The application must automatically aggregate annual payroll history and dependent filings, compute final personal income tax liability, and scaffold GDT statutory Form 05/QTT-TNCN in XML format compatible with HTKK.

## Relevant Product Docs

- `docs/product/v16_roadmap.md`

## Acceptance Criteria

- [ ] Implement aggregation logic to compile year-to-date taxable income, dependents, exemptions, and withheld taxes.
- [ ] Recalculate individual PIT liability using Vietnam's progressive tax brackets and flat rate exceptions.
- [ ] Scaffold statutory Form 05/QTT-TNCN and its Appendices (05-1, 05-2, 05-3) in GDT-compliant XML format.
- [ ] Provide a comparison dashboard to review tax refunds or additional payments due.
- [ ] Expose API endpoint `POST /api/pit/finalize` to trigger the finalization and export the XML file.
- [ ] Write unit tests verifying annual tax bracket aggregation, dependent calculation, and XML structure.

## Design Notes

- **Module**: `invoices/pit_finalizer.py`
- **Output**: GDT HTKK-ready XML template serialization.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v16_pit_finalizer.py` checking annual progressive tax calculations and dependent exemption rules |
| Integration | Generating the XML finalization returns a structured file validating against GDT Form 05 schema |
