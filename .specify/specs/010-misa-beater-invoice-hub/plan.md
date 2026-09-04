# Implementation Plan: MISA meInvoice Beater - Next-Gen GDT Invoice Hub

## Files That Change
1. `invoices/routes/core.py` - Core PDF View & Compliance Audit Endpoint.
2. `templates/invoice_pdf.html` - Wise Fintech Bento Grid Portal & Tab Control Bar.
3. `templates/tax_compliance_hub.html` - Enterprise Tax Compliance Dashboard.
4. `tests/test_pdf.py` - Unit test suite validating Circular 99/2025/TT-BTC and IFRS standards.

## Order of Work (Thin Vertical Slices)
1. **Slice 1 (Accounting Engine)**: Enhance `api_invoice_pdf_view` in `core.py` to calculate double-entry journal vouchers for Circular 99/2025/TT-BTC and audit Circular 219 non-cash rules.
2. **Slice 2 (Bento Grid UI)**: Refactor `invoice_pdf.html` to integrate dark glassmorphism top navigation bar, 4 interactive tabs, and CA signature inspector.
3. **Slice 3 (Verification & Testing)**: Run `pytest tests/test_pdf.py` to ensure 100% binary pass rate.
4. **Slice 4 (Localhost Browser Audit)**: Run Flask dev server on `http://127.0.0.1:5000` and perform visual QA using `browser_subagent`.

## Proof of Correctness
- `python -m pytest tests/test_pdf.py -k test_invoice_pdf_view_accounting_standards` exits with **Code 0**.
- `GET http://127.0.0.1:5000/api/invoices/<invoice_id>/pdf-view` returns HTTP **200 OK** with Circular 99/2025 and IFRS metadata.
