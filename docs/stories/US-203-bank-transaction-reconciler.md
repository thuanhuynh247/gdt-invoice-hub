# Story Specification: US-203 — Corporate Banking Transaction Reconciler

## 📋 Context & Business Value
Validating that purchase invoices are actually paid is crucial, especially since input VAT deductions in Vietnam are only allowed for invoice values above 20 million VND if they are paid via non-cash bank transfers. This story implements an automated bank statement parser and invoice reconciler to track payment fulfillment and ensure compliance.

---

## 🎯 Acceptance Criteria

### 1. Bank Statement Excel & CSV Parser
- **Requirement**: Parse corporate bank statement exports from major Vietnamese commercial banks (e.g. Vietcombank, BIDV, Techcombank, Vietinbank).
- **Extracted Fields**:
  - Transaction Date & Time
  - Reference / Document Number
  - Debit/Credit Amount
  - Counterparty Bank Account Number & Name
  - Transfer Description / Narration text

### 2. Fuzzy Payment Matcher
- **Requirement**: Implement a heuristic matching algorithm.
- **Matching Rules**:
  - Parse invoice numbers (e.g. `0001234` or `1234`) or invoice symbols (e.g. `1C26TBA`) from transfer narrations.
  - Reconcile payments matching counterparties' tax codes or legal names.
  - Handle multi-invoice consolidated transfers and partial payments.

### 3. Compliance Flagging
- **Requirement**: Flag high-risk transactions.
- **Rules**:
  - Alert if a purchase invoice with value > 20,000,000 VND has no recorded bank payment matching the seller name.
  - Alert if the payment was sent to a personal bank account instead of the seller's registered corporate account.

---

## 🛠️ Verification & Test Plan

- **Unit Tests**:
  - Test narration text parsing regex on edge cases (e.g. `thanh toan hd 1234, 1235 ky hieu C26TBA`).
  - Test threshold matching for invoice amounts.
- **Integration Tests**:
  - Upload a mock VCB statement spreadsheet to `POST /api/payments/bank-recon`.
  - Assert that transactions matching database invoice totals are marked as "Reconciled/Paid" and exceptions are returned.
