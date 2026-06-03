# Story Specifications — Version 18.0.0 IFRS Translation & OECD Compliance

## 📌 Epics & Stories Covered:
- **Epic E85: IAS 12 Deferred Tax** -> **US-300: IAS 12 Temporary Difference Engine** & **US-301: Deferred Tax Balance Sheet Integration**
- **Epic E86: IFRS 16 Leases** -> **US-302: Present Value Calculator** & **US-303: Lease Liability Amortization Schedule**
- **Epic E87: OECD Pillar Two** -> **US-304: Cross-Tenant Consolidation Router** & **US-305: GloBE Top-up Tax Estimator**

---

## 📖 1. Business Requirements & Objective
To enable mid-market and enterprise entities to scale globally and prepare for international audits, GDT Invoice Hub translates localized tax data under Vietnamese Accounting Standards (VAS) into International Financial Reporting Standards (IFRS) compliance reporting.

---

## ⚙️ 2. Architectural & Technical Specifications

### 2.1 IAS 12 Deferred Tax Temporary Difference Engine (US-300, US-301)
- **Database Tables (isolated per tenant)**: `ifrs_deferred_tax_ledger`
- **Dynamic Rules**:
  - Compares the **Carrying Amount under IFRS** against the **Tax Base under VAS**.
  - Determines temporary taxable/deductible differences:
    - *Liability item*: if Carrying Amount < Tax Base -> **Deferred Tax Liability (DTL)**. if Carrying Amount > Tax Base -> **Deferred Tax Asset (DTA)**.
    - *Asset item*: if Carrying Amount > Tax Base -> **Deferred Tax Liability (DTL)**. if Carrying Amount < Tax Base -> **Deferred Tax Asset (DTA)**.
  - Automatic persistence of calculations back into SQLite ledger.

### 2.2 IFRS 16 Lease Present Value Amortization Engine (US-302, US-303)
- **Database Tables**: `lease_amortization_schedule`
- **Schedule Formulation**:
  - Automatically discounts monthly lease payments at incremental borrowing discount rates to calculate the initial **Right-of-Use (ROU) Asset** value.
  - Computes month-by-month schedules showing: Opening Balance, Payment, Interest Expense (Finance cost), Principal Repayment, and Closing Balance.

### 2.3 OECD Pillar Two GloBE Top-up Tax Estimator (US-304, US-305)
- **Cross-Tenant Consolidation Router**:
  - Programmatically loops through isolated tenant databases (`tenant_<mst>.db`) to extract net income and tax liabilities under Ultimate Parent MST configuration.
- **GloBE Tax Calculations**:
  - Computes consolidated Effective Tax Rate (ETR).
  - Flags ETR drops below the international **15% GloBE minimum rate**.
  - Calculates substance-based exclusions and predicted top-up tax liabilities.

---

## 🧪 3. Verification & Test Evidence (Pytest Suite)

All calculations are fully verified by the automated testing suite:
- `tests/test_ifrs_engine.py` (Passes 6/6 tests)
- `tests/test_compliance_routes.py` (Passes 7/7 REST routes)

```text
tests\test_ifrs_engine.py ......                                         [100%]
============================== 6 passed in 4.75s ==============================

tests\test_compliance_routes.py .......                                  [100%]
============================== 7 passed in 1.12s ==============================
```
