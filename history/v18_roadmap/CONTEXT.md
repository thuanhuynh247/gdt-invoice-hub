# Version 18.0.0: Enterprise IFRS Compliance & Global Tax Optimization - Context

**Feature slug:** v18_roadmap
**Date:** 2026-06-02
**Exploring session:** active
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 18.0.0 introduces **Enterprise IFRS Compliance & Global Tax Optimization**, establishing corporate reporting bridges between statutory Vietnamese Accounting Standards (VAS) and International Financial Reporting Standards (IFRS), alongside global minimum tax estimation. The feature boundary includes:
1. **IAS 12 Deferred Tax Engine**: Calculates Deferred Tax Assets (DTA) and Deferred Tax Liabilities (DTL) by comparing carrying amounts vs. tax bases under VAS/IFRS.
2. **IFRS 16 Lease Amortization Auditor**: Calculates the Present Value (PV) of lease obligations to scaffold Right-of-Use (ROU) assets and amortization schedules.
3. **OECD Pillar Two GloBE Estimator**: Implements dynamic Effective Tax Rate (ETR) calculation and Substance-Based Income Exclusion (SBIE) rules across isolated tenants to estimate global top-up liabilities.

---

## 🔒 Locked Decisions

These decisions are locked to guide downstream planning:

- **D18-1: Temporary Difference Detection & Mapping Rules**
  - **Decision**: The system will automatically compare asset carrying amounts with the tax base to recognize DTA (carrying < tax base) or DTL (carrying > tax base) at a standard rate of 20%.
  - **Rationale**: Standardizes international tax audit procedures while maintaining alignment with local CIT declarations.
- **D18-2: Discounted Cash Flow Present Value Formulation**
  - **Decision**: Present Value (PV) of lease obligations under IFRS 16 will use a parameterized annual discount rate, split monthly, to generate Right-of-Use asset values.
  - **Rationale**: Eliminates manual spreadsheets and provides dynamic tracking of principal and interest repayments.
- **D18-3: Cross-Tenant Effective Tax Rate Router**
  - **Decision**: To calculate the OECD Pillar Two ETR, the system will utilize a secure cross-tenant consolidation router that aggregates net accounting income and adjusted covered taxes.
  - **Rationale**: Safely evaluates the global ETR per jurisdiction across isolated tenant databases.
- **D18-4: Substance-Based Income Exclusion (SBIE) Defaults**
  - **Decision**: Substance-Based Income Exclusions (SBIE) will apply standard default coefficients (e.g., 8% of payroll and tangible assets) to reduce the top-up tax base.
  - **Rationale**: Directly conforms to the model GloBE rules issued by the OECD.

---

## 🔍 Existing Code & Reusable Context

Our quick scout has identified several high-value assets and integration seams inside the workspace:

### 1. Reusable Assets
- [ifrs_engine.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/ifrs_engine.py) — Contains the core engines for IFRS 16 calculations, IAS 12 deferred tax, and OECD Pillar Two estimation.
- [test_ifrs_engine.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_ifrs_engine.py) — Test suite containing assertions for DTA/DTL, IFRS 16 amortization tables, and GloBE ETR.

### 2. Integration Seams
- [routes.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes.py) — Needs endpoints to expose IFRS reconciliation tables and GloBE Top-up calculations.

---

## 🚀 Handoff Note

Exploring phase is complete. The product boundaries, architectural decisions, and integration guidelines for Version 18.0.0 are fully locked in `CONTEXT.md`.
