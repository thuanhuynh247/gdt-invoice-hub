# Story Specification: US-201 — Trial Balance & Ledger Integrity Auditor

## 📋 Context & Business Value
Tax audits regularly penalize companies for mismatched accounting entries where transactions are recorded in the general ledger (Sổ cái) but lack a corresponding XML e-invoice (Hóa đơn đầu vào/đầu ra), or vice versa. This story implements an automated integrity checker that audits ledger accounts against GDT-authenticated invoice archives.

---

## 🎯 Acceptance Criteria

### 1. Ledger-to-Invoice Matcher
- **Requirement**: Cross-reference transactions recorded in the purchases journal (Debit `152`, `153`, `156`, `642` / Credit `331`, `111`, `112`) and sales journal (Credit `511`, `3331` / Debit `131`, `111`, `112`) with valid XML invoices.
- **Matching Fields**:
  - Buyer/Seller Tax Code (MST)
  - Invoice Date vs Journal Entry Date (within a customizable 30-day window)
  - Total amount before tax, VAT rate, and total amount after tax

### 2. Discrepancy Detection & Alert Engine
- **Requirement**: Identify and flag typical accounting mistakes.
- **Rules**:
  - **Flag "Invoice Missing"**: Transaction exists in ledger but no XML invoice matches.
  - **Flag "Ledger Entry Missing"**: XML invoice exists in database but no matching ledger transaction is found.
  - **Flag "Value Mismatch"**: Mapped transaction and invoice exist, but tax values, total amounts, or tax rates differ.

### 3. Reporting API
- **Requirement**: Endpoint to upload the Trial Balance (Bảng cân đối số phát sinh) and General Ledger files to compile a compliance report.
- **Endpoint**: `POST /api/bctc/audit-ledger`
- **Output**: JSON containing arrays of `missing_invoices`, `missing_entries`, and `value_mismatches` with severity scores.

---

## 🛠️ Verification & Test Plan

- **Unit Tests**:
  - Verify matching algorithm works with dates on different timezones.
  - Test threshold matching for minor rounding differences (e.g. less than 10 VND).
- **Integration Tests**:
  - Run matching loop on a database containing 5 test purchase XML invoices and a ledger containing 6 entries (one unlinked).
  - Verify that the API output returns 1 `missing_invoice` alert.
