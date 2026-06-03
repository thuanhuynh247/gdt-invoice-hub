# Version 19.0.0: Enterprise Tax Compliance & Dynamic Multi-Tenant Audit Oracle - Context

**Feature slug:** v19_roadmap
**Date:** 2026-06-02
**Exploring session:** active
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 19.0.0 introduces the **Enterprise Tax Compliance & Dynamic Multi-Tenant Audit Oracle**, an advanced module designed to elevate the GDT Invoice Hub into an enterprise-grade tax intelligence platform. The feature boundary encapsulates three major Vietnamese tax compliance pillars:
1. **Related-Party & Transfer Pricing Compliance (Decree 132/2020/NĐ-CP)**: Mapping of related relationships, EBITDA interest cap audit logic (30% cap), and automated **Form 01/132-NĐ-CP** compilation.
2. **Foreign Contractor Tax (FCT) Withholding Auditor (Circular 103/2014/TT-BTC)**: Intelligent scanning of cross-border service expenses, FCT withholding tax splits (VAT and CIT), and **Form 01/NTNN** tax return generator.
3. **CIT Scenario Modeler, Preferred Rates & R&D Fund Planner (Circular 78/2014/TT-BTC & Circular 80/2021/TT-BTC)**: Dynamic simulations of R&D fund allocations (up to 10% tax shield), corporate preferential tax rates (10%, 15%), and tax holidays.

---

## 🔒 Locked Decisions

These decisions are locked to guide downstream planning:

- **D19-1: Strict 30% EBITDA Interest Deduction Cap**
  - **Decision**: The system will automatically compute EBITDA using `EBITDA = Net Operating Profit + Net Interest Expense + Depreciation` and enforce the 30% interest expense deduction limit under Decree 132/2020/NĐ-CP.
  - **Rationale**: Keeps net interest expense deductions strictly aligned with transfer pricing limits, flagging any excess as non-deductible expense (Chỉ tiêu B4 on CIT return).
- **D19-2: Automated Circular 103 FCT Split Logic**
  - **Decision**: Invoices flagged under FCT will apply the Circular 103/2014/TT-BTC withholding rates: 5% VAT and 5% CIT for services; 5% VAT and 2% CIT for services attached to goods; 10% CIT for royalties; and VAT exempt + 5% CIT for SaaS/Software.
  - **Rationale**: Standardizes withholding calculation rules, minimizing audit exposure for cross-border transactions.
- **D19-3: Detailed Decree 132 Related-Party Letter Mappings**
  - **Decision**: The system will support a related-party catalog where each vendor is mapped to their specific Decree 132 relationship code (A through L). This data will be persisted and used to compile the official Form 01/132-NĐ-CP transaction breakdown.
  - **Rationale**: Locks Option A from Socratic Probe Q1, ensuring fully detailed related-party compliance reporting rather than simple binary flags.
- **D19-4: Line-Item Level Circular 103 FCT Auditing**
  - **Decision**: The FCT auditor will calculate VAT and CIT withholdings at the individual line-item level, aggregating totals for the Form 01/NTNN return based on line-item categories (Software, Royalty, Technical Service, etc.).
  - **Rationale**: Locks Option A from Socratic Probe Q2, allowing highly precise tax deduction auditing for contracts containing mixed-service/mixed-goods deliverables.
- **D19-5: Dynamic Tax Holiday & Preferred CIT Rates Modeler**
  - **Decision**: The system will implement a fully dynamic Tax Holiday engine that allows enterprise users to input custom preferred CIT rates (e.g., 10%, 15%), specify custom years of 100% tax exemption, and specify custom years of 50% tax reduction to simulate multi-year corporate tax liability projections under Circular 78/2014/TT-BTC.
  - **Rationale**: Locks Option A from Socratic Probe Q3, ensuring the platform can simulate custom hi-tech zone tax holidays and R&D incentives dynamically over multiple fiscal years, rather than a hardcoded set of scenarios.

---

## 🔍 Existing Code & Reusable Context

Our quick scout has identified several high-value assets and integration seams inside the workspace:

### 1. Reusable Assets
- [cit_service.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/cit_service.py) — Core CIT calculation engine, contains basic EBITDA cap logic (`pretax_profit + interest_expense_635 + depreciation_214`) and standard HTKK 03/TNDN XML generator.
- [supplier_risk_service.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/supplier_risk_service.py) — Supplier risk calculation, late signing check, and suspicious items text scanning logic.
- [test_fct_auditor.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_fct_auditor.py) — Contains comprehensive unit tests for FCT contractors (Google, Zoom, AWS), asserting VAT/CIT withholding calculation and Form 01/NTNN exports.

### 2. Integration Seams
- [routes.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes.py) — Needs to be extended with new endpoints for Related Party management, FCT returns, and CIT simulations.
- [models.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/models.py) — Can support related party identifiers or FCT settings using dynamic configurations or standard catalogs.

---

## 🚨 Socratic Gray-Area Probes (Outstanding Decisions)

All Socratic decisions have been successfully resolved and locked:
1. **Q1 (Decree 132 Related-Party)** resolved as **Option A** (Detailed Decree 132 Related-Party Letter Mappings D19-3).
2. **Q2 (Circular 103 Mixed FCT)** resolved as **Option A** (Line-Item Level Circular 103 FCT Auditing D19-4).
3. **Q3 (Circular 78 Tax Holiday)** resolved as **Option A** (Dynamic Tax Holiday & Preferred CIT Rates Modeler D19-5).

---

## 🚀 Handoff Note

Exploring phase is complete. All 3 Vietnamese tax compliance pillars (Decree 132 Related-Parties, Circular 103 FCT line-item split, and Circular 78 dynamic CIT Tax Holidays) have their product boundaries and architectural decisions fully locked in `CONTEXT.md`. We are now ready to transition to the planning phase using `using-khuym:planning`.
