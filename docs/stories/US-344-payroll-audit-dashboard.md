# Story Specification: US-344 — Interactive Payroll Audit Dashboard

## 📋 Context & Business Value
Provides a web-based dashboard visual interface for payroll audit compliance, displaying employee payroll registries, progressive PIT tax brackets (5% to 35%), and statutory social insurance calculations in real time.

---

## 🎯 Acceptance Criteria
- **Interactive Web Interface**:
  - Render an employee payroll table showing gross salary, deductions (social insurance, personal deduction, dependent deduction), taxable income, PIT withheld, and net pay.
  - Alert the auditor if PIT or SI withheld deviates from statutory rules.
- **API Endpoint**:
  - `GET /api/payroll/audit-summary` returning aggregate metrics (total headcount, gross payroll, PIT variance, insurance compliance score).

---

## 🛠️ Verification & Test Plan
- Run unit test verifying payroll metrics API:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v22_payroll_pit.py"
  ```
