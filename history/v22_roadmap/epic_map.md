# Epic Map - Version 22.0.0: Intelligent Tax Penalty Predictor & Advanced Corporate Tax Compliance

## Feature Outcome
An automated audit and compliance dashboard enabling statutory interest prediction, multi-channel e-commerce order reconciliation, and payroll PIT Form 05/QTT-TNCN wizard returns.

---

## Epics

### Epic E97: Statutory Tax Penalty & Explanation Builder
- **Outcome**: Automatically calculates under-declaration/evasion tax penalties (Decree 125/2020/NĐ-CP) and drafts defense templates.
- **Complexity**: Medium

### Epic E98: E-Commerce Reconciliation Engine
- **Outcome**: Normalization and reconciliation of CSV/JSON feeds from platforms (Shopee, Lazada, TikTok Shop) against GDT e-invoices.
- **Complexity**: High

### Epic E99: PIT & Payroll Dashboard
- **Outcome**: Progressively computes PIT and generates valid XML packages for Form 05/QTT-TNCN.
- **Complexity**: Medium

---

## Story Queue

| Story ID | Title | Epic | Status | Dependencies |
| --- | --- | --- | --- | --- |
| `US-340` | Statutory Tax Penalty & Interest Calculator | Epic E97 | Implemented | None |
| `US-341` | AI-Generated Audit Explanation & Defense Template Builder | Epic E97 | Implemented | `US-340` |
| `US-342` | Shopee, Lazada & TikTok Shop Order Normalizer | Epic E98 | Implemented | None |
| `US-343` | E-Commerce Tax Compliance Matching & Warning Engine | Epic E98 | Implemented | `US-342` |
| `US-344` | Interactive Payroll Audit Dashboard | Epic E99 | Implemented | None |
| `US-345` | PIT Finalizer & Form 05/QTT-TNCN UI | Epic E99 | Implemented | `US-344` |

---

## Current Story to Prepare: `US-345`
- **Objective**: Complete step-by-step PIT finalization and export HTKK-compliant XML schemas.
