# Story Specification: US-392 — Pre-Audit Corporate Tax Risk Scoring Engine

## 📋 Context & Business Value
To prepare companies for tax audits, the system needs to evaluate accounting data and raise a Tax Risk Index (0-100) along major compliance vectors (Related Party transactions, blacklisted suppliers, cash limits, delay in invoice timing, and cancellation patterns).

---

## 🎯 Acceptance Criteria
- **Multi-Vector Risk Modeler**:
  - Calculate scores (0-100) for 5 distinct risk categories:
    1. **Related Party Risks**: Related-party interest expense exceeding 30% of EBITDA (Decree 132).
    2. **Supplier Blacklist Matches**: Purchases from known blacklisted suppliers (or high-risk tax statuses).
    3. **Invoicing Latency**: Invoices issued >10 days after delivery note date (Decree 123).
    4. **Cash Limit Violations**: Individual cash transactions >= 20M VND (Circular 219).
    5. **Cancellation Ratios**: Count of cancelled invoices divided by total invoices exceeding a threshold (e.g., 10%).
  - Output a combined weighted Tax Risk Scorecard JSON payload.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v27_features.py -k test_pre_audit_risk_engine"
  ```
