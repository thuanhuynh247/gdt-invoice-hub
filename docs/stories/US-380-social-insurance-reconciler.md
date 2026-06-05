# Story Specification: US-380 — Social Insurance (BHXH/BHYT/BHTN) Reconciliation & Auditing Engine

## 📋 Context & Business Value
To automate payroll compliance, the system needs an auditing engine to verify employee salaries and payroll items against statutory social insurance (BHXH/BHYT/BHTN) contribution rates, basic wage limits, and report discrepancies.

---

## 🎯 Acceptance Criteria
- **Social Insurance Contribution Engine**:
  - Calculate statutory social insurance contribution rates: employer contribution (21.5% total: 17.5% BHXH, 3% BHYT, 1% BHTN) and employee contribution (10.5% total: 8% BHXH, 1.5% BHYT, 1% BHTN).
  - Verify that the contribution wage does not exceed the statutory cap of 20 times the basic salary (allow basic salary config, e.g. 1,800,000 VND or 2,340,000 VND).
- **Discrepancy Reporting**:
  - Compare payroll list wages with actual social insurance filing records (which can be mock input) and report differences.
  - Return detailed audit reports detailing calculations for each employee, flags for caps exceeded, and mismatch amounts.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest tests/test_v26_features.py"
  ```
