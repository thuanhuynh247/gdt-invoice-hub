# Epic Map - Version 20.0.0: Enterprise Tax AI Swarm & Real-time Audit Network

## Feature Outcome
A highly integrated tax management platform deploying a collaborative tax agent swarm, real-time bank transaction streaming, and seasonal ML tax liability projections.

---

## Epics

### Epic E91: Tax AI Agent Swarm (Harness v2.0-aligned)
- **Outcome**: Secure peer-to-peer message broker (Local Mailroom) and autonomous joint audit coordinator agent parsing prompts and delegating audits.
- **Complexity**: High

### Epic E92: Bank Stream Ingestion & Matching
- **Outcome**: Normalized parsing of ISO 20022 bank statements mapped to active purchase/sales VAT invoices with confidence scoring.
- **Complexity**: Medium

### Epic E93: ML Tax Forecast & Sandbox
- **Outcome**: 12-month forward seasonal predictive VAT/CIT liability modeling and interactive tax planning sandbox.
- **Complexity**: High

---

## Story Queue

| Story ID | Title | Epic | Status | Dependencies |
| --- | --- | --- | --- | --- |
| `US-320` | Local Agent Mailroom & Coordination Hub | Epic E91 | Todo | None |
| `US-321` | Autonomous Joint Audit Coordinator | Epic E91 | Todo | `US-320` |
| `US-322` | Bank Feed Ingestion & Transaction Normalizer | Epic E92 | Todo | None |
| `US-323` | Automated Bank-to-Invoice Matcher | Epic E92 | Todo | `US-322` |
| `US-324` | Machine Learning Tax Liability Predictor | Epic E93 | Todo | None |
| `US-325` | Tax Scenario Simulation Sandbox | Epic E93 | Todo | `US-324` |

---

## Current Story to Prepare: `US-320`
- **Objective**: Create the SQLite schema for local P2P agent communications (AgentInbox, AgentOutbox), expose Python APIs for agent message dispatch/retrieve, and write basic tests checking P2P integration.
