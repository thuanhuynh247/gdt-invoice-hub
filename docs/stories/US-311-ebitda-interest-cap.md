# Story Specification: US-311 — Core EBITDA Interest Cap & Form 01/132 Disclosures

## 📋 Context & Business Value
Under Clause 3, Article 16 of Decree 132/2020/NĐ-CP, the total deductible net interest expense of a taxpayer having related-party transactions must not exceed 30% of their EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization). This story calculates corporate EBITDA, flags non-deductible interest limits, and scaffolds the required disclosure structures.

---

## 🎯 Acceptance Criteria

### 1. EBITDA Calculation Engine
- Calculate EBITDA using the corporate financial figures:
  $$\text{EBITDA} = \text{Net Operating Profit} + \text{Net Interest Expense} + \text{Depreciation}$$
- Net Interest Expense is defined as `Interest Expense - Interest Income`.
- If the Net Interest Expense exceeds $30\%$ of the calculated EBITDA, the excess amount is classified as non-deductible for CIT finalization.
- Generate warning payloads showing the cap threshold and the excess amount.

### 2. Form 01/132-NĐ-CP Scaffolder
- Construct structured data mapping to Form 01/132-NĐ-CP disclosures:
  - Related-party list with name, relationship code, transaction volume, and valuation adjustments.
  - Net Interest calculation and EBITDA limit assessment.
- Support XML exporting structured according to GDT standard templates (for HTKK compatibility).

---

## 🛠️ Verification & Test Plan
- Run Pytest verification using `tests/test_cit.py`.
- Verify the calculations under both normal interest and cap-exceeded scenarios, asserting correct non-deductible values.
