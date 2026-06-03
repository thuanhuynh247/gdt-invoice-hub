# Story Specification: US-335 — Import VAT Reconciliation & Mitigation

## 📋 Context & Business Value
To detect discrepancies in import tax declarations, the reconciliation engine matches customs declarations with payment receipts and import invoices, generating variance mitigation reports.

---

## 🎯 Acceptance Criteria
- **Reconciliation Rules**: Compare exchange rates, declared HS codes, and import VAT payment differences against purchase invoices.
- **Reporting Output**: Map mismatch differences and automatically drafts adjustments.
- **API Endpoint**:
  - `POST /api/customs/reconcile` to compute reconciliation matches and draft variance reports.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying customs reconciliation logic:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_customs_reconciler.py -k test_customs_reconciliation"
  ```
