# Current Story Pack: US-160 - Tax Deadline Alerter

## Context & Alignment
- **Epic**: E70
- **Story ID**: `US-160`
- **Objective**: Implement Tax Deadline Alerter core logic.

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
