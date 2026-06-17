# Current Story Pack: US-180 - CIT Calculation & Form 03/TNDN Scaffolder

## Context & Alignment
- **Epic**: E76
- **Story ID**: `US-180`
- **Objective**: Implement CIT Calculation & Form 03/TNDN Scaffolder core logic.

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
