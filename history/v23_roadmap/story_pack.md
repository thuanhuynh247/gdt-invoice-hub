# Story Pack - Version 23.0.0: Exporter VAT Refund, ERP Webhooks & Local Ollama Tax RAG

This story pack covers the entire implementation of US-350 to US-355.

## Story Queue & Progress

- **US-350: Input VAT Evaluator Engine**
  - **Status**: Implemented
  - **Deliverable**: Checks supplier MST active status, flags >20M VND invoices without bank payment matching, and matches customs declarations.
- **US-351: Form 01/ĐNHT Refund Packet Wizard**
  - **Status**: Implemented
  - **Deliverable**: Step-by-step wizard creating XML dossiers for Form 01/ĐNHT export returns.
- **US-352: Secure Versioned REST API Gateway**
  - **Status**: Implemented
  - **Deliverable**: HMAC-SHA256 signature verifier gateway preventing replay and unauthorized access.
- **US-353: ERP Webhook Dispatcher & Registry**
  - **Status**: Implemented
  - **Deliverable**: Event-based subscriptions and transactional dispatches with automatic backoff retry algorithms.
- **US-354: Offline Ollama Tax Regulations RAG**
  - **Status**: Implemented
  - **Deliverable**: Local DB RAG searching official decrees (Decree 123, 125, Circular 80) with citation mapping.
- **US-355: Advisory Chat & Defense Panel UI**
  - **Status**: Implemented
  - **Deliverable**: Chat application and explanation draft template generator UI for taxpayers.

## Verification & Proof

- **Unit Proof**:
  - `tests/test_v27_features.py`
  - `tests/test_vat_refund.py`
- **Integration Proof**:
  - `invoices/routes.py` and front-end interface endpoints.
