# Story Specification: US-382 — Electronic Tax Ledger (Sổ thuế điện tử) Sync & Reconciliation Engine

## 📋 Context & Business Value
To maintain synchronization between local tax records and the official GDT records, the system needs an engine to fetch the taxpayer's electronic tax ledger, showing liabilities, paid tax, credits, and interest on late payments, and reconcile them with internal accounting accounts.

---

## 🎯 Acceptance Criteria
- **e-Tax Ledger Parser & Sync**:
  - Simulate pulling the e-tax ledger showing outstanding tax liabilities (CIT, VAT, etc.), late payment interests, and overpayments/credits.
- **Reconciliation Module**:
  - Reconcile local tax payments and liability journals against the synced ledger.
  - Return lists of matching transactions and flagging unresolved differences (e.g. tax paid in local records but not reflected on GDT, or late fees computed on GDT).

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest tests/test_v26_features.py"
  ```
