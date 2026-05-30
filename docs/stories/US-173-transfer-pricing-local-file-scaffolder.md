# US-173 Transfer Pricing Local File Scaffolder

## Status

planned

## Lane

normal

## Product Contract

The application must offer an automated setup wizard to compile corporate and transactional profiles, generating a compliant Transfer Pricing Local File (.docx) matching Ministry of Finance requirements.

## Relevant Product Docs

- `docs/product/v14_roadmap.md`
- Nghị định 132/2020/NĐ-CP (Appendix I Form 01)

## Acceptance Criteria

- [ ] Build a multi-step TP Local File configuration wizard UI.
- [ ] Auto-extract related-party transaction tables from database to populate Appendix I.
- [ ] Implement local file Word (.docx) generation with structured sections: Company Profile, Related Party Relationships, Pricing Methods, and Transaction Details.
- [ ] Support exporting Appendix I (Mẫu số 01) format to spreadsheet/Word files.
- [ ] Write tests verifying report builder data bindings.

## Design Notes

- **Module**: `invoices/tp_doc_generator.py`.
- **Pricing Methods**: Support selection of Transactional Net Margin Method (TNMM), Comparable Uncontrolled Price (CUP), or Cost Plus.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v14_tp_scaffolder.py` verifying template data mapping |
| Integration | Generating Local File returns download stream for `.docx` and `.xlsx` Appendix I |
