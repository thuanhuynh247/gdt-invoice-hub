# Story Specification: US-343 — E-Commerce Tax Compliance Matching & Warning Engine

## 📋 Context & Business Value
To detect un-invoiced revenue or pricing discrepancies, the system reconciles platform sales orders against official electronic tax invoices issued by the merchant.

---

## 🎯 Acceptance Criteria
- **Reconciliation & Warnings**:
  - Reconcile e-commerce platform sales against issued e-invoices.
  - Pair by Order ID in invoice notes/description or by Buyer Name/Phone match.
  - Raise `UNINVOICED_SALES_WARNING` for completed orders lacking a matching e-invoice.
  - Raise `PRICE_MISMATCH_WARNING` if the price difference is greater than 1,000 VND.
- **API Endpoint**:
  - `GET /api/ecommerce/reconcile` returning unmatched orders, matched invoices, and a reconciliation summary.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying matching logic:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v22_ecommerce.py"
  ```
