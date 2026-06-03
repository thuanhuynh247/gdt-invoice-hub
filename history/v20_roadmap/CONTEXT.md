# Version 20.0.0: Enterprise Tax AI Swarm & Real-time Audit Network - Context

**Feature slug:** v20_roadmap
**Date:** 2026-06-03
**Exploring session:** active
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 20.0.0 introduces the **Enterprise Tax AI Swarm & Real-time Audit Network**, designed to transition GDT Invoice Hub's intelligence from a single AI auditor to a collaborative multi-agent swarm, while integrating real-time banking telemetry. The feature boundary encapsulates three major enterprise pillars:
1. **Multi-Agent Tax Advisory Swarm (Harness v2.0-aligned)**: An asynchronous peer-to-peer message broker (Mailroom) allowing specialized local agents (VAT Auditor, PIT Auditor, Transfer Pricing Auditor) to collaborate and resolve complex multi-tax exposure questions autonomously.
2. **Real-time Bank-to-Invoice Stream Processing**: Automated ingestion and normalization of ISO 20022 bank transaction statements, mapped against active VAT sales/purchase invoices with automated matching scoring and risk warning badging.
3. **Machine Learning Tax Liability Predictor & Sandbox**: 12-month forward predictive forecasting of CIT and VAT liabilities using seasonality-aware regression models, coupled with an interactive sandbox dashboard to simulate corporate structural tax holiday scenarios.

---

## 🔒 Locked Decisions

These decisions are locked to guide downstream planning:

- **D20-1: Peer-to-Peer Agent Mailroom Architecture**
  - **Decision**: The multi-agent communication framework must utilize an asynchronous, database-backed inbox/outbox messaging queue (P2P Mailroom broker) to prevent execution bottlenecks.
  - **Rationale**: Ensures robust task routing and audit logging between isolated specialized agents without requiring live network calls.
- **D20-2: Standardized ISO 20022 and Bank Statement Normalization**
  - **Decision**: Ingested bank feeds will be normalized into a standard BankLedger SQLite table containing transaction date, amount, sender/recipient account, sender/recipient MST, and transaction memo.
  - **Rationale**: Provides a uniform integration interface supporting major Vietnamese banks (Techcombank, Vietcombank, BIDV) out of the box.
- **D20-3: Rule-Based Matcher with Confidence Scoring**
  - **Decision**: The bank-to-invoice matching engine will score match confidence from 0% to 100% based on combined criteria (MST match, payment reference code string matching, and value matching within 0.1% tolerance).
  - **Rationale**: Minimizes false matches and alerts financial teams with specialized audit warnings for cash transactions >= 20M VND not backed by bank records.
- **D20-4: Seasonal ARIMA/Prophet Predictor for VAT/CIT**
  - **Decision**: Liability projections must incorporate historical tax cycles (seasonality) over a minimum of 12 rolling months, outputting a visual confidence interval band (95% range).
  - **Rationale**: Prevents naive linear extrapolation which fails during Vietnam's Tet holiday seasonal transaction drops.

---

## 🔍 Existing Code & Reusable Context

Our quick scout has identified several high-value assets and integration seams inside the workspace:

### 1. Reusable Assets
- [harness_win.py](file:///d:/LearnAnyThing/Webapp%20XML/scripts/harness_win.py) — Telemetry and agent tracing database schemas, providing the blueprint for local agent mailroom tracking.
- [cit_service.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/cit_service.py) — Core CIT calculation formulas and scenario analysis.
- [test_analytics.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_analytics.py) — Base forecasting algorithms and regression tests.

### 2. Integration Seams
- [routes.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes.py) — Extension endpoints for AI Swarm interactions, Bank ledger management, and interactive forecast rendering.

---

## 🚀 Handoff Note

Exploring phase is complete. The product boundaries, architectural decisions, and integration guidelines for Version 20.0.0 (Tax AI Swarm, Bank Ingestion & Matching, and ML Tax Projections) are fully locked in `CONTEXT.md`.
