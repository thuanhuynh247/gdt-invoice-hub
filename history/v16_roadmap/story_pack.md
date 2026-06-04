# Current Story Pack: US-190 - Customs XML Parser & Import-Export Duty Calculator

## Context & Alignment
- **Epic**: E79
- **Story ID**: `US-190`
- **Objective**: Implement Customs XML Parser & Import-Export Duty Calculator core logic.

---

## 🚪 Entry State
- Features are stubbed or partially integrated with basic schemas.

---

## 🏁 Exit State
- Clean, verified logic with dedicated API endpoints.
- Integration verified via the test suite.

---

## 📂 Files Likely Touched
- `invoices/routes.py`
- Services in `invoices/`
- Test files in `tests/`

---

## 🔍 Feasibility Assumptions & Risk Mitigations
- **Assumption**: Input data conforms to Vietnam GDT format guidelines.
  - *Mitigation*: Fallback to standard validation envelopes.

---

## 🧪 Verification Plan
- **Tests Execution**:
  - Run the test suite: `python scripts/harness_win.py validate` or equivalent.

---

## 🛑 Out of Scope
- Advanced integration features (covered in subsequent user stories).
