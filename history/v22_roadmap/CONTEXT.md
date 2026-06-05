# Version 22.0.0: Intelligent Tax Penalty Predictor & Advanced Corporate Tax Compliance - Context

**Feature slug:** v22_roadmap
**Date:** 2026-06-04
**Exploring session:** completed
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 22.0.0 introduces the **Intelligent Tax Penalty Predictor & Advanced Corporate Tax Compliance** suite, which automates calculations for statutory tax penalties, late payment interest, e-commerce matching, and payroll/PIT audit dashboards. The feature boundary includes:
1. **Statutory Tax Penalty & Interest Calculator**: Implements automated computations of tax penalties under Decree 125/2020/NĐ-CP and daily interest of 0.03% on under-declared tax.
2. **E-Commerce Reconciliation Engine**: Normalizes and matches Shopee, Lazada, and TikTok Shop order details against issued e-invoices, raising mismatch alerts when declarations deviate.
3. **PIT & Payroll Dashboard**: Interactive audit panel for salary registers against progressive PIT rates (5% to 35%) and social insurance withholdings, with step-by-step UI to finalize PIT Form 05/QTT-TNCN XML returns.

---

## 🔒 Locked Decisions

- **D22-1: Penalty and Daily Late Payment Calculations**
  - **Decision**: Set the tax under-declaration penalty rate to exactly 20% of the underpaid tax amount, and the late payment interest rate to 0.03% per day calculated from `due_date + 1` to `calculation_date`. Evasion penalty multipliers must be configurable from 1.0x to 3.0x of the tax amount.
- **D22-2: E-Commerce Reconciliation Tolerance Threshold**
  - **Decision**: Flag any e-commerce orders completed but missing matching e-invoices, or where the invoice total differs from payment received by more than 1,000 VND.
- **D22-3: PIT Progressive Tax Brackets & Social Insurance Rates**
  - **Decision**: Implement the 7 progressive PIT brackets (5% up to 5M, 10% 5M-10M, 15% 10M-18M, 20% 18M-32M, 25% 32M-52M, 30% 52M-80M, 35% over 80M) and social insurance rates (10.5% employee, 21.5% employer). Output Form 05/QTT-TNCN XML structured matching GDT's HTKK schema.

---

## 🔍 Existing Code & Reusable Context

### 1. Reusable Assets
- `invoices/models.py` — Base tables for storing invoices and taxpayer profiles.
- `invoices/routes.py` — Web endpoints mapping.

### 2. Integration Seams
- `templates/advanced_audit.html` — Layout UI mapping.
- `static/js/main.js` — Client side controllers for interactive features.

---

## 🚀 Handoff Note

Exploring phase is complete. The boundaries, architectural decisions, and integration guidelines for Version 22.0.0 are fully locked in `CONTEXT.md`.
