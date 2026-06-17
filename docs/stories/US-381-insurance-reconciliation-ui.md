# Story Specification: US-381 — PIT Finalization Settlement & Insurance Reconciliation Dashboard UI

## 📋 Context & Business Value
This story provides an interactive UI dashboard allowing tax managers to review the discrepancy reports between payroll records, social insurance reports, and PIT settlements, with download exports.

---

## 🎯 Acceptance Criteria
- **Interactive Dashboard**:
  - A summary card display showing total social insurance differences (employer and employee), count of flagged employees, and PIT settlement status.
  - A comparison table rendering each employee's base salary, calculated social insurance contributions, actual contribution, mismatch flags, and PIT standard deduction calculations.
- **Export Action**:
  - Allow downloading the social insurance reconciliation report as a formatted CSV document.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest tests/test_v26_features.py"
  ```
