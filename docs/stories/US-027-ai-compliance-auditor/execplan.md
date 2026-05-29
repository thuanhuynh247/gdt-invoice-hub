# Exec Plan

## Goal
Introduce an AI-powered semantic auditing engine to analyze invoice items and unit prices, flagging tax-deductibility anomalies and price inflations, and persisting results in SQLite.

## Scope

In scope:
- Integration of an LLM client supporting local Ollama (Llama-3/Qwen) and OpenAI/Gemini APIs.
- Semantic prompt engineering for Vietnamese tax rules on deductible business expenses.
- Database schema update: add `ai_warnings` column or a separate `AIAuditResult` table to `invoices.db`.
- Front-end integration: render AI warnings with distinct badge styling (e.g., purple/indigo) in the invoice Offcanvas drawer and PDF/modal views.
- Configuration panel updates: fields for selecting AI provider (Ollama, OpenAI, Gemini), model name, API key, and system prompts.

Out of scope:
- Training custom local models (only prompt engineering and RAG-based context matching are used).
- Full accounting software ledger synchronization.

## Risk Classification

Risk flags:
- **Data model**: Adding columns/tables to SQLite schema.
- **Audit/security**: Processing financial data via third-party LLM APIs.
- **External systems**: Connecting to Ollama endpoint or external AI APIs.
- **Public contracts**: Exposing new API response fields and settings schemas.
- **Existing behavior**: Intercepting and adding onto the existing invoice import/save pipeline.

Hard gates:
- No API keys or credentials must be hardcoded in the codebase or settings logs.
- AI network requests must not block the main Flask thread; auditing should run asynchronously or fail gracefully if the model is offline.

## Work Phases

1. **Discovery**: Research Ollama performance with lightweight models (Llama-3-8B, Qwen-2.5-7B) on invoice text in Vietnamese.
2. **Design**: Plan database tables, API JSON request/response schema, and setting configuration interfaces.
3. **Validation planning**: Define test cases with mock LLM responses.
4. **Implementation**:
   - Update database schema.
   - Implement LLM auditor client and prompt parser.
   - Refactor UI settings and invoice views.
5. **Verification**: Run E2E Selenium tests simulating LLM connections and warning badge rendering.
6. **Harness update**: Add execution results to test matrix and stories.

## Stop Conditions

Pause for human confirmation if:
- Ollama response latency is too high (exceeds 5 seconds per invoice), necessitating a background worker queue for AI audits.
- The user prefers to restrict the scope to APIs (Gemini/OpenAI) rather than local models.
