# US-026: PDF Invoice Export and Printing

## Status

implemented

## Lane

normal

## Product Contract

The application must allow users to download a standard printable PDF file for any electronic invoice or tax report directly from the system. The PDF must look identical to the "Mẫu Đỏ" (Red Template) Vietnamese invoice and contain all corporate metadata, line items, and audit markers.

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)

## Acceptance Criteria

- [x] Add a "Tải PDF" (Download PDF) button to the interactive toolbar of the Invoice Preview Modal.
- [x] Implement backend PDF generation using a library such as `Weasyprint` or `xhtml2pdf` (or Playwright page PDF screenshot export) that converts the HTML template directly into a clean vector PDF.
- [x] The generated PDF must preserve the correct CSS styles (fonts, red borders, signature stamps) and be split perfectly into pages if there are multiple pages of line items.
- [x] File naming convention must match: `invoice_{invoice_id}.pdf`.
- [x] Add a PDF export action to the Partner Directory and BC26 usage reports to export reports as PDF documents.

## Design Notes

- **Libraries**: `weasyprint` (requires GTK+) or `reportlab` / `playwright` for headless HTML to PDF rendering.
- **Page Layout**: Letter or A4 size, with correct print margins defined in CSS `@media print`.
- **UI Surfaces**:
  - Download PDF button next to Print button in the modal toolbar.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Backend test verifying PDF generation returns a valid PDF byte buffer |
| Integration | API test verifying `/api/invoices/<id>/pdf` returns `application/pdf` headers |
| E2E | Visual validation checking that fonts are rendered properly without truncation |

## Harness Delta

None.

## Evidence

None.
