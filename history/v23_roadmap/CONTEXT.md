# Version 23.0.0: Exporter VAT Refund, ERP Webhooks & Local Ollama Tax RAG - Context

**Feature slug:** v23_roadmap
**Date:** 2026-06-05
**Exploring session:** completed
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 23.0.0 introduces the **Exporter VAT Refund, ERP Webhooks & Local Ollama Tax RAG** suite, designed to streamline exporting compliance audits, automate real-time updates via ERP webhooks, and provide secure API integration along with offline regulations advisory. The feature boundary includes:
1. **Input VAT Evaluator Engine (Circular 80/2021/TT-BTC)**: Verifies supplier tax codes (MST), matches customs declarations (Tờ khai Hải quan) against export invoices, and automatically flags input invoices > 20M VND lacking bank payment confirmation records.
2. **Form 01/ĐNHT Refund Packet Wizard**: Generates and compiles valid GDT-compliant dossier XML files representing Form 01/ĐNHT.
3. **Secure Versioned Gateway & Webhooks**: Provides HMAC-SHA256 signature authorization for API versioning and a stateful webhook hub for transactional triggers with automatic backoffs and retries.
4. **Offline RAG & Interactive Advisory Chat**: Uses Ollama local LLM instance to query tax regulation databases (Decree 123, 125, Circular 80) and render inline citations.

---

## 🔒 Locked Decisions

- **D23-1: Customs & Export Match Constraints**
  - **Decision**: Match export invoices to customs declarations on buyer MST, product description/quantity, and currency total. Flag any invoice exceeding 20M VND paid in cash as non-eligible.
- **D23-2: HMAC-SHA256 Signature Header Authorization**
  - **Decision**: All versioned REST API calls under `/api/v1/*` must be verified via `X-GDT-Signature` header calculated using `hmac_sha256(SECRET_KEY, timestamp + "." + query_string_or_body)`. Timestamps older than 5 minutes must be immediately rejected to prevent replay attacks.
- **D23-3: Webhook Backoff Retry Strategy**
  - **Decision**: Webhook failures must trigger a exponential retry backoff schedule (delay = $2^{retry} \times 10$ seconds) up to a max of 3 retry attempts before marking the delivery as failed.
- **D23-4: Local Ollama Tax Regulations RAG**
  - **Decision**: Run RAG on a local SQLite regulations table using Ollama models, falling back to regex citation matching if Ollama is unreachable offline, ensuring continuous system operation.

---

## 🔍 Existing Code & Reusable Context

### 1. Reusable Assets
- `tests/test_vat_refund.py` — In-house unit tests for verifying VAT refund parameters.
- `invoices/refund_service.py` — Core logic for calculating VAT refund structures.

### 2. Integration Seams
- `invoices/webhook_hub.py` — Webhook worker.
- `invoices/ai_tax_advisor.py` — Local RAG matching and advice composer.

---

## 🚀 Handoff Note

Exploring phase is complete. The boundaries, architectural decisions, and integration guidelines for Version 23.0.0 are fully locked in `CONTEXT.md`.
