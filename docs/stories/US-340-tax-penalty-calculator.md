# Story Specification: US-340 — Statutory Tax Penalty & Interest Calculator

## 📋 Context & Business Value
To help businesses assess their audit risk exposures under Vietnamese tax laws, the system must automatically calculate potential penalties (pursuant to Decree 125/2020/NĐ-CP) and daily late payment interest (0.03% per day) on tax variances.

---

## 🎯 Acceptance Criteria
- **Penalty Logic**:
  - Calculate under-declaration penalty of **20%** of the underpaid tax amount.
  - Calculate late interest of **0.03% per day** starting from `due_date + 1` up to the user-supplied calculation date.
  - EVASION penalty multiplier option (1.0x to 3.0x of the tax amount).
- **API Endpoint**:
  - `POST /api/audit/calculate-penalties` returning the computed penalties, late interest, and total liability.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying calculations:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v22_tax_audit.py"
  ```
