# Story Specification: US-391 — Delivery-to-Invoice Reconciliation Dashboard UI

## 📋 Context & Business Value
Accounting professionals must ensure that what is shipped matches what is invoiced. The system needs to reconcile PXK SKU details against commercial invoices and expose mismatches on a visual dashboard.

---

## 🎯 Acceptance Criteria
- **Reconciliation Engine**:
  - Compare line-item quantities in the delivery note (PXK) against line-item quantities in the invoice linked by reference number.
  - Flag any variances where quantity delivered is greater than or less than quantity invoiced.
- **Interactive UI**:
  - Provide a dashboard showing matched records, unmatched delivery notes (delivered but not invoiced), and unmatched invoices (invoiced but no delivery note).
  - Export CSV reconciliation report detailing discrepancy values.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v27_features.py -k test_delivery_invoice_matching"
  ```
