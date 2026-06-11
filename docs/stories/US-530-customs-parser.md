# Spec: US-530 — Export Customs Declaration XML Parser

## Status

planned

## Lane

normal

## Product Contract

The system parses export customs declaration XML files (Tờ khai hải quan xuất khẩu) from the General Department of Customs. It extracts:
- Declaration Number (`Số tờ khai`)
- Customs Clearance Date (`Ngày thông quan` or `Ngày giải phóng hàng`)
- Taxpayer MST (`MST người xuất khẩu`)
- Total Export Value in USD & VND (`Trị giá USD / VND`)
- Exchange Rate (`Tỷ giá tính thuế`)
- HS Codes & Item Description list.

## Acceptance Criteria

- [ ] Provide an XML parsing function inside `invoices/v41_service.py` to extract all required fields.
- [ ] Add `CustomsDeclaration` database model to store parsed customs declaration information.
- [ ] Render a mock XML file uploader in the web UI for testing customs declaration uploads.
- [ ] Handle bad XML formats or missing clearance dates gracefully.

## Validation

- `tests/test_v41_features.py::test_customs_declaration_parser`
