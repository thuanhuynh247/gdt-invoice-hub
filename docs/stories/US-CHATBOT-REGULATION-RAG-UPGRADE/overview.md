# Overview: Enterprise AI Chatbot RAG Upgrade (Dynamic Ingestion & Glassmorphic Chat UX)

## Current Behavior

Currently, the local AI Tax Advisory Chatbot (`AIChatAgent` inside `invoices/ai_service.py`) operates with several architectural limitations:
1. **Static Knowledge Base**: Legal tax regulations are hardcoded directly into Python lists (`TAX_REGULATIONS`). The PDF files `luat48.pdf` (VAT Law 48) and `luat149.signed.pdf` (VAT Law 149) in the workspace are not dynamically read or ingested.
2. **Brittle Keyword Routing**: Queries are routed to contexts using simple regex string matching against hardcoded lists of keywords. This leads to poor semantic relevance and fails when queries use synonym variations.
3. **No Thread Memory / Persistence**: Chats are in-memory or lack durable, multi-session databases. Sessions are lost on application restart, preventing audit histories.
4. **Basic UI styling**: The front-end interface uses vanilla styles without high-fidelity glassmorphism, responsive micro-animations, or dynamic markdown rendering of tabular query outputs.

---

## Target Behavior

The upgraded system will deliver a production-grade, dynamic, and visually stunning local RAG chatbot experience:
1. **Background PDF Ingestion Pipeline**: A background worker scans the workspace for tax PDFs (`luat48.pdf`, `luat149.signed.pdf`), extracts page layouts using `pypdf`, partitions text into semantic blocks (Articles, Chapters, and Paragraphs), and populates a new SQLite model `TaxRegulationChunk`.
2. **SQLite FTS5 Full-Text Search**: The chatbot leverages a high-speed SQLite Full-Text Search (`fts5`) virtual table `tax_regulation_fts` to calculate semantic relevance scores, delivering far higher search accuracy than static regex.
3. **Durable Chat Persistence**: Chat sessions (`AIChatSession`) and messages (`AIChatMessage`) are stored durably in the local SQLite database, allowing users to switch taxpayers, resume past audits, or export chat transcripts.
4. **State-of-the-Art UX (Glassmorphism designkit style)**:
   - **Vibrant Dark/Light Themes**: Uses customized HSL CSS design tokens for premium aesthetics.
   - **Floating Glassmorphic Chat Drawer**: Modern absolute floating container with a `backdrop-filter: blur(16px)` glass style, subtle floating shadow, and micro-transitions.
   - **Markdown Rendering & Tables**: Full rendering support for complex text, markdown lists, bullet points, and SQLite SQL-to-table query answers.

---

## Affected Users

* **Corporate Accountants & Tax Advisors**: Who need immediate, highly accurate answers on new VAT regulations (Law 48/2024 & Law 149/2025) and deductible thresholds.
* **Compliance Auditors**: Who need to verify system-generated audit badges, draft corporate mitigation explanations, and view historical compliance chat traces.
* **System Administrators**: Who configure local/external AI endpoints (Ollama/Gemma-4, Gemini, OpenAI).

---

## Affected Product Docs

* `docs/stories/US-CHATBOT-REGULATION-RAG.md` (Linked baseline story)
* `docs/product/ai_tax_compliance_spec.md` (Product specifications)
* `API_SPEC.md` (Adding chat session, message list, and query endpoints)

---

## Non-Goals

* **Heavy External Vector DBs**: We explicitly reject using heavy, external Vector databases (like Pinecone, Milvus, or Qdrant) to maintain the zero-dependency, single-file SQLite database portability of the meInvoice platform.
* **Scanned PDF OCR inside Flask thread**: Doing raw image OCR on scanned PDF pages dynamically inside Flask. For scanned PDFs (such as signing stamps in `luat149.signed.pdf`), we will rely on structured text metadata layers, high-fidelity OCR pre-extraction scripts, or graceful text-empty fallback modes.
