# Epic Map - Version 23.0.0: Exporter VAT Refund, ERP Webhooks & Local Ollama Tax RAG

## Feature Outcome
A production-grade exporter tax dossier wizard, a robust event-driven webhook hub, and an offline interactive regulation advisor powered by local LLM RAG.

---

## Epics

### Epic E100: Form 01/ĐNHT Refund Wizard
- **Outcome**: Implements the Circular 80/2021/TT-BTC evaluator audit engine and Form 01/ĐNHT XML package generation.
- **Complexity**: High

### Epic E101: Secure Versioned API & Webhooks
- **Outcome**: A secure REST gateway featuring HMAC-SHA256 request signing and a robust webhook dispatch hub.
- **Complexity**: Medium

### Epic E102: Ollama Tax regulations RAG
- **Outcome**: Offline LLM vector query engine over local tax regulation documents with defense letter automation templates.
- **Complexity**: High

---

## Story Queue

| Story ID | Title | Epic | Status | Dependencies |
| --- | --- | --- | --- | --- |
| `US-350` | Input VAT Evaluator Engine | Epic E100 | Implemented | None |
| `US-351` | Form 01/ĐNHT Refund Packet Wizard | Epic E100 | Implemented | `US-350` |
| `US-352` | Secure Versioned REST API Gateway | Epic E101 | Implemented | None |
| `US-353` | ERP Webhook Dispatcher & Registry | Epic E101 | Implemented | `US-352` |
| `US-354` | Offline Ollama Tax Regulations RAG | Epic E102 | Implemented | None |
| `US-355` | Advisory Chat & Defense Panel UI | Epic E102 | Implemented | `US-354` |

---

## Current Story to Prepare: `US-355`
- **Objective**: Deploy advisory chat panel in the front-end that connects to the RAG system and auto-drafts Decree 125 tax penalty explanations.
