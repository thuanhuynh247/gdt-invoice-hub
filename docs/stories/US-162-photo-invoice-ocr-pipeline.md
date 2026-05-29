# US-162 Photo Invoice OCR Pipeline

## Status

planned

## Lane

high_risk

## Product Contract

The application must accept uploaded invoice images (JPEG, PNG, scanned PDF) and extract structured invoice data fields using a local OCR engine, presenting an editable preview for user verification before persisting.

## Relevant Product Docs

- `docs/product/v13_roadmap.md`

## Acceptance Criteria

- [ ] Implement upload endpoint `POST /api/invoices/ocr-upload` accepting image files.
- [ ] Extract key fields: seller_name, seller_mst, invoice_number, invoice_date, line_items, vat_amount, total.
- [ ] Display extraction preview UI with editable fields for user correction.
- [ ] Use ddddocr as primary engine with Tesseract fallback for complex layouts.
- [ ] Handle error cases: corrupted files, unreadable images, unsupported formats.
- [ ] Achieve >80% field extraction accuracy on standard Vietnamese invoice templates.
- [ ] Write tests with sample invoice image fixtures.

## Design Notes

- **Module**: New `invoices/ocr_pipeline.py`.
- **Privacy**: All processing local — zero cloud upload per D3 decision.
- **Supported formats**: JPEG, PNG, PDF (first page).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v13_ocr_pipeline.py` with fixture images |
| Integration | Upload → preview → save flow produces valid Invoice records |
