# Spec: US-532 — Form 01-1/GTGT Export VAT List Builder

## Status

completed

## Lane

normal

## Product Contract

The system aggregates cleared and matched export transactions to auto-compile the export goods list (Bảng kê hàng hóa, dịch vụ xuất khẩu mẫu 01-1/GTGT) as specified in Circular 80/2021/TT-BTC.

## Acceptance Criteria

- [x] Extract all matched export declarations and invoices for a specific tax taxpayer and period.
- [x] Compile them into standard Circular 80 Form 01-1/GTGT columns: customs number, registration date, invoice number, invoice date, export revenue, and tax rate (0%).
- [x] Render the Form 01-1/GTGT list in the web UI.

## Validation

- `tests/test_v41_features.py::test_form_01_1_gtgt_builder`
