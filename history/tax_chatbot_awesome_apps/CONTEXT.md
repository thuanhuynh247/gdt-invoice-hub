# Tax Chatbot Awesome Apps - Context

**Feature slug:** tax_chatbot_awesome_apps
**Date:** 2026-06-27
**Exploring session:** complete
**Scope:** Standard
**Domain types:** SEE | CALL | ORGANIZE | RUN

## Feature Boundary

This feature upgrades the existing `/tax-advisor` workspace into a production-ready agentic RAG chatbot, adopting proven patterns from the `Shubhamsaboo/awesome-llm-apps` repository. It integrates multi-agent dynamic routing badges, real-time conversation metrics (latency, token estimation, active RAG chunks count), dynamic visual calculation widgets (Generative UI cards for FCT, penalty, and PIT calculations), and cleaner citation formatting.

## Locked Decisions

These are fixed. Planning must implement them exactly.

- **D1 (Wise Glassmorphic Chat Workspace):** Maintain and enhance the `/tax-advisor` page layout. Keep the left sidebar for taxpayer selector and session histories. The chat body will display a new glassmorphic status bar at the top displaying current taxpayer profile details and active Chat Metrics (Latency, Estimated Tokens, Active RAG Chunks, Current Agent Category).
- **D2 (Dynamic Multi-Agent Status):** Each incoming assistant reply will dynamically display the specialized agent's badge (e.g., "Chuyên gia Giao dịch liên kết", "Chuyên gia Thuế TNCN", etc.) with its distinct gradient background and custom icon to signify which specialist handled the query.
- **D3 (Generative UI & Calculation Cards):** Enhance the backend RAG & calculator services (`invoices/tax_advisor_service.py`) to inject custom HTML-based calculator widgets directly inside chat bubbles for:
  - **FCT Calculator Widget** (Calculates contractor VAT/CIT with net/gross selection).
  - **Penalty Calculator Widget** (Calculates late filing/payment penalties under Decree 125).
  - **PIT Calculator Widget** (Simulates personal income tax liability with family deduction rules).
- **D4 (Clean Metadata Citations):** Format RAG citation references under the message text as distinct clickable pill components listing the source document (e.g. *Nghị định 123/2020/NĐ-CP*, *Luật Thuế GTGT 48/2024/QH15*), page number, and interactive text tooltips.

### Agent's Discretion

- The agent has discretion over layout spacing, colors, icons selection (Bootstrap Icons), and standard tooltip formatting.
- The agent has discretion over latency estimation calculations on the frontend (e.g., calculating request duration via JS timestamps).

## Existing Code Context

### Reusable Assets

- `invoices/tax_advisor_service.py`: Contains RAG logic (`get_rag_context`), dynamic suggestions (`generate_dynamic_suggestions`), and calculator detection logic (`detect_and_run_tools`).
- `invoices/routes/core.py`: Exposes `/api/tax/chat`, `/api/tax/chat/suggest-questions`, and session endpoints.
- `templates/tax_advisor.html`: The frontend user interface for the general tax advisor chatbot.

### Established Patterns

- **RAG Context Integration:** RAG chunks are retrieved from `tax_regulation_chunk` in SQLite using keyword indexing.
- **Ollama/Gemini Integration:** LLM requests are processed through `call_llm(settings, system_prompt, user_message, history)` in `tax_advisor_service.py`.

## Canonical References

- [invoices/tax_advisor_service.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/tax_advisor_service.py) - RAG and calculation routing.
- [templates/tax_advisor.html](file:///d:/LearnAnyThing/Webapp%20XML/templates/tax_advisor.html) - Chatbot frontend template.

## Outstanding Questions

- None.

## Deferred Ideas

- Local Vector Embedding Database (e.g., ChromaDB/FAISS) deferred per resource boundaries. FTS5 indexing remains the primary retrieval pipeline.
