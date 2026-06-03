# Story Specification: US-314 — Preferential CIT Rates, Tax Holidays & R&D Modeler

## 📋 Context & Business Value
Vietnam offers tax incentives under Circular 78/2014/TT-BTC, such as corporate preferential tax rates (10%, 15%), multi-year tax exemptions and reductions (tax holidays), and science and technology development (R&D) fund shielding. This story implements dynamic modelers to test and project the tax savings under these incentive structures.

---

## 🎯 Acceptance Criteria

### 1. Preferential CIT Rate Modulations
- Allow simulating and applying custom preferential corporate tax rates (e.g., 10% or 15% instead of the default 20% statutory rate).

### 2. Tax Holidays & Reductions
- Support configuring custom tax holiday stages:
  - **Exemption Stage**: N years at 100% tax exemption (CIT due = 0).
  - **Reduction Stage**: M years at 50% tax reduction (CIT due halved).
- Calculate CIT finalization adjusting for these dynamic timelines.

### 3. Science & Technology (R&D) Fund Shielding
- Allow setting aside up to 10% of taxable income to a science and technology (R&D) fund.
- Shield the allocated R&D amount from CIT calculation (deducted directly from taxable income before rate application).

---

## 🛠️ Verification & Test Plan
- Run Pytest verification using `tests/test_cit.py` and `tests/test_ifrs_engine.py`.
- Verify the math of tax exemptions, CIT rate overrides, and R&D deductions against expected CIT due.
