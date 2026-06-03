# Approach - Version 18.0.0: Enterprise IFRS Compliance & Global Tax Optimization

## Recommended Approach

### 1. IFRS IAS 12 Engine Implementation (`invoices/ifrs_engine.py`)
- We will construct the `IFRSEngine` class featuring a dynamic method `calculate_temporary_differences`.
- Compare carrying amounts under IFRS vs. tax bases under VAS for both assets and liabilities:
  - **Deferred Tax Asset (DTA)** is recognized when the carrying amount of an asset is less than its tax base, or when the carrying amount of a liability is greater than its tax base.
  - **Deferred Tax Liability (DTL)** is recognized when the carrying amount of an asset is greater than its tax base, or when the carrying amount of a liability is less than its tax base.
  - The engine must support evaluating loss carry-forwards to determine if future taxable profits permit DTA recognition.
  - Integrate these calculations into the balance sheet view as adjusting journal entries.

### 2. IFRS 16 Lease Present Value & Amortization (`invoices/ifrs_engine.py`)
- Create methods to discount future lease payments:
  - $$PV = \text{Payment} \times \left[\frac{1 - (1 + r)^{-n}}{r}\right]$$
  - Build an amortization table that splits monthly rents into:
    - **Interest Expense** (carrying value of liability * monthly rate).
    - **Principal Repayment** (total monthly payment - interest expense).
  - Return the right-of-use asset value and liability balances for monthly disclosure schedules.

### 3. OECD Pillar Two GloBE Estimator (`invoices/ifrs_engine.py`)
- Standardize the Effective Tax Rate (ETR) calculation at the jurisdictional level:
  - $$\text{ETR} = \frac{\text{Adjusted Covered Taxes}}{\text{Net GloBE Income}}$$
- Apply Substance-Based Income Exclusion (SBIE) rules using a default 8% rate on payroll and tangible assets:
  - $$\text{Top-up Tax Base} = \text{Net GloBE Income} - \text{SBIE}$$
- Compute the top-up tax rate ($15\% - \text{ETR}$) and final top-up tax liability.

### 4. Cross-Tenant Query Consolidation Routing (`invoices/routes.py`)
- Construct an administrative route `/api/ifrs/consolidate` allowing authorized users to safely poll and aggregate net income, covered taxes, payroll, and assets across isolated tenant databases (`tenant_<mst>.db`).

---

## Risk Map & Mitigation Strategies

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Database isolation locks during consolidation | Medium | Use WAL mode and configure a busy timeout of 30,000ms. |
| Inconsistent carrying value formats | Medium | Enforce strict schemas when importing IAS 12 balance sheet rows. |
| Incorrect discount rate calculations | Low | Add extensive unit tests covering extreme parameters (e.g. 0% discount rate). |
