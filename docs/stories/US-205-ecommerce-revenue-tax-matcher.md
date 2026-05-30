# Story Specification: US-205 — Multi-Channel Revenue & Tax Reconciliation Engine

## 📋 Context & Business Value
Vietnam's tax authorities are aggressively auditing e-commerce sellers, comparing shipping data and platform payouts with declared e-invoices to detect tax evasion. This story implements a reconciliation engine that matches platform order logs with official GDT output invoices, flagging un-invoiced revenue and ensuring VAT claims on platform fees are fully backed by GDT-registered input invoices.

---

## 🎯 Acceptance Criteria

### 1. Sales-to-Invoice Matcher
- **Requirement**: Match Shopee/TikTok Shop order IDs against e-invoice notes/descriptions in the GDT output database.
- **Rules**:
  - For B2B orders: Match single e-invoices issued to the specific corporate buyer.
  - For retail orders: Ensure they are aggregated and mapped to the daily consolidated retail output invoice (Hóa đơn bán lẻ xuất gộp cuối ngày).

### 2. Discrepancy Auditing & Alerts
- **Requirement**: Flag typical e-commerce compliance gaps:
  - **Un-invoiced Revenue**: Platform records show order completed and paid, but no matching GDT output invoice exists.
  - **VAT Deduction Risk**: Platform charged a commission/service fee, but no valid input invoice has been registered from Shopee/TikTok in the GDT archives.

### 3. Dashboard API
- **Requirement**: Endpoint `GET /api/ecommerce/reconcile` returning summary discrepancy rates, missing invoices lists, and audit risk scores.

---

## 🛠️ Verification & Test Plan

- **Unit Tests**:
  - Test aggregation of retail orders into daily totals for consolidated invoice matches.
- **Integration Tests**:
  - Run matching on mock database with 10 e-commerce orders (3 un-invoiced).
  - Verify that the reconciliation report returns exactly 3 discrepancies and a high tax risk warning.
