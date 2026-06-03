# Story Specification: US-200 — Statutory Financial Statements (BCTC) Scaffolder

## 📋 Context & Business Value
Under Circular 200/2014/TT-BTC, corporate entities in Vietnam must prepare and submit annual Financial Statements (Báo cáo Tài chính - BCTC) to the General Department of Taxation. This story automates compiling the Balance Sheet (B01-DN), Income Statement (B02-DN), and Cash Flow Statement (B03-DN) from the General Ledger, drastically reducing manual entry friction and preventing rounding errors.

---

## 🎯 Acceptance Criteria

### 1. General Ledger Mapping & Aggregation
- **Requirement**: Parse General Ledger records (Excel or JSON format) and group them by standard VAS (Vietnamese Accounting Standards) account numbers.
- **Rules**:
  - Map cash balance accounts (`111`, `112`) to Balance Sheet Line "Cash and cash equivalents" (Mã số 110).
  - Map short-term trade receivables (`131`) to Balance Sheet Line "Short-term trade receivables" (Mã số 131).
  - Map trade payables (`331`) to Balance Sheet Line "Short-term trade payables" (Mã số 311).
  - Map tax liabilities (`333` and sub-accounts) to Balance Sheet Line "Taxes and other obligations to the State Budget" (Mã số 313).

### 2. Financial Equation Integrity Check
- **Requirement**: Enforce strict balance validations before export.
- **Rules**:
  - Total Assets (Mã số 270) MUST equal Total Equity and Liabilities (Mã số 440).
  - Net Profit After Tax on the Income Statement (Mã số 60) must match the increase in Undistributed Earnings on the Balance Sheet (Mã số 421) after year-end adjustments, unless dividends are paid.

### 3. XML Export Format for HTKK
- **Requirement**: Produce an XML payload compatible with the GDT's HTKK software import tool.
- **Format**:
  - Root element: `<HSoKhaiThue>` containing standard metadata (Tax Code, Business Name, Reporting Period, VAS Template Type).
  - Child elements: `<BangCanDoiKeToan>`, `<BaoCaoKetQuaKinhDoanh>`, `<BaoCaoLuuchuyenTienTe>`.

---

## 🛠️ Verification & Test Plan

- **Unit Tests**:
  - Verify that a list of ledger balances maps correctly to the target Balance Sheet fields.
  - Verify that the asset-liability equality assertion flags a mismatch with a clear validation error.
- **Integration Tests**:
  - Invoke `POST /api/bctc/compile` with a set of VAS transaction logs.
  - Assert that the returned payload is valid HTKK XML and matches expected totals.
