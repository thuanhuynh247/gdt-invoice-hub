# Story Specification: US-323 — Automated Bank-to-Invoice Matcher

## 📋 Context & Business Value
To verify payment compliance, the system matches ingested bank transactions against sales/purchase invoices using fuzzy description lookup and invoice reference numbers. High-value transactions (>= 20M VND) without matches must trigger warnings.

---

## 🎯 Acceptance Criteria
- **Matching Heuristics**:
  - Matches invoice numbers or IDs found in transaction descriptions.
  - Directional matching (Credit matches sales invoices, Debit matches purchases).
  - Exact or partial amount reconciliation.
- **Safety Alerts**: Highlight unmatched high-value transactions (>= 20,000,000 VND).
- **API Endpoint**:
  - `POST /api/bank/match` to run transaction matching.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying matcher accuracy and alert thresholds:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_bank_matching.py -k test_transaction_matching_heuristics"
  ```
