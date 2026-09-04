# Specification: MISA meInvoice Beater - Next-Gen GDT Invoice Hub

## Functional Requirements
- **[FR-1] Automated Prefetch & Session Renewal Daemon** (Maps to `[PRB-2]`, `[OUT-2]`):
  - Pre-solves GDT CAPTCHAs in background queues.
  - Maintains active session tokens for automated invoice fetching without human intervention.
- **[FR-2] Circular 99/2025/TT-BTC Accounting Engine** (Maps to `[PRB-3]`, `[OUT-3]`):
  - Auto-maps Purchase/Sales invoices to GL accounts (Nợ TK 1561/1331 - Có TK 331; Nợ TK 131 - Có TK 5111/33311).
  - Explicitly states compliance with Circular 99/2025/TT-BTC (effective Jan 1, 2026).
- **[FR-3] Decree 123 & Circular 219 Tax Audit Engine** (Maps to `[PRB-4]`, `[OUT-4]`):
  - Scans invoice amount; if `total_amount >= 20,000,000 VND`, generates `non_cash_warning`.
  - Audits seller MST validity against GDT database and assigns Tax Rating `A+`.
- **[FR-4] IFRS & Peppol BIS Billing 3.0 Interoperability** (Maps to `[PRB-5]`, `[OUT-5]`):
  - Fetches Vietcombank (VCB) live FX rates.
  - Provides Peppol Profile `urn:fdc:peppol.eu:2017:poacc:billing:01:1.0` metadata.
- **[FR-5] Wise Fintech Bento Grid Portal** (Maps to `[PRB-6]`, `[OUT-6]`):
  - Tab 1: `📄 Hóa Đơn Đỏ (VAS)`
  - Tab 2: `📊 Bút Toán Nợ/Có (TT 99/2025)`
  - Tab 3: `🌐 Chuẩn Quốc Tế (IFRS)`
  - Tab 4: `🔍 XML Inspector & CA`

## API Contracts & Data Model
- Endpoint: `GET /api/invoices/<invoice_id>/pdf-view`
  - Response: Rendered HTML dashboard with full compliance metadata.
- Response JSON / Template Context:
  ```json
  {
    "invoice": { "id": "...", "amount": 1540000 },
    "journal_entries": [
      { "account_code": "1561", "account_name": "Hàng hóa...", "debit": 1400000, "credit": 0 },
      { "account_code": "1331", "account_name": "Thuế GTGT...", "debit": 140000, "credit": 0 },
      { "account_code": "331", "account_name": "Phải trả...", "debit": 0, "credit": 1540000 }
    ],
    "compliance_audit": {
      "requires_bank_transfer": false,
      "cit_deductible": true,
      "vat_deductible": true,
      "tax_rating": "A+ (Chỉ số Tuân thủ Cao)",
      "accounting_standard": "Thông tư 99/2025/TT-BTC (Thay thế TT 200/2014/TT-BTC từ 01/01/2026)"
    },
    "ifrs_data": {
      "currency": "VND",
      "fx_rate": 1.0,
      "peppol_profile": "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
    }
  }
  ```
