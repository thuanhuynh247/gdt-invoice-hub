# US-173 Transfer Pricing Local File Scaffolder

## Status

implemented

## Lane

normal

## Product Contract

The application must offer an automated setup wizard to compile corporate and transactional profiles, generating a compliant Transfer Pricing Local File (.docx) matching Ministry of Finance requirements.

## Relevant Product Docs

- `docs/product/v14_roadmap.md`
- Nghị định 132/2020/NĐ-CP (Appendix I Form 01)

## Acceptance Criteria

- [x] Build a multi-step TP Local File configuration wizard UI.
- [x] Auto-extract related-party transaction tables from database to populate Appendix I.
- [x] Implement local file Word (.docx) generation with structured sections: Company Profile, Related Party Relationships, Pricing Methods, and Transaction Details.
- [x] Support exporting Appendix I (Mẫu số 01) format to spreadsheet/Word files.
- [x] Write tests verifying report builder data bindings.

## Design Notes

- **Module**: `invoices/tp_doc_generator.py`.
- **Pricing Methods**: Support selection of Transactional Net Margin Method (TNMM), Comparable Uncontrolled Price (CUP), or Cost Plus.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v14_tp_scaffolder.py` verifying template data mapping |
| Integration | Generating Local File returns download stream for `.docx` and `.xlsx` Appendix I |
