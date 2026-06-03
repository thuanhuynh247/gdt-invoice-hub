# Exec Plan: Enterprise AI Chatbot RAG Upgrade (Dynamic Ingestion & Glassmorphic Chat UX)

## Goal

Transition the meInvoice local AI Tax Chatbot from static, hardcoded regulation keyword lists to a **dynamic PDF-ingesting, SQLite FTS5-indexed RAG system** backed by a **premium, durable chat interface**.

---

## Scope

### In scope:
1. **Dynamic PDF Parser Pipeline**:
   - Background startup worker using `pypdf` to extract text from `luat48.pdf` and `luat149.signed.pdf` in the root workspace.
   - Text splitter utility to clean Vietnamese whitespace, partition text into semantic paragraphs (150–250 words), and associate chunks with page numbers, law ID, and effective dates.
2. **SQLite Durable Indexing Layer**:
   - Schema Migration: Database model `TaxRegulationChunk` mapping chunk fields.
   - SQLite FTS5 Virtual Table `tax_regulation_fts` to enable high-efficiency lexical and BM25-based semantic query matching.
   - Context retrieval function replacing `get_tax_rag_context` to dynamically query FTS5 and return the top 3 scoring segments.
3. **Multi-Session Chat & Memory**:
   - Database model `AIChatSession` (fields: `id`, `taxpayer_mst`, `title`, `created_at`).
   - Database model `AIChatMessage` (fields: `id`, `session_id`, `role`, `content`, `created_at`).
   - REST API endpoints for session creation, history loading, and streaming message queries in `invoices/routes.py`.
4. **State-of-the-Art Interface (designkit style)**:
   - Floating Glassmorphic Chat Sidebar overlaying `templates/invoices.html`.
   - Backdrop filter styling (`backdrop-filter: blur(16px); background: rgba(255, 255, 255, 0.7);` or dark variant).
   - Typing indicator micro-animations, automatic vertical scroll adjustments, and Markdown parsing engine for clean tabular displays.

### Out of scope:
* **Local Python Vector Embeddings (BERT/SentenceTransformers)**: Excluded to prevent high CPU/RAM overhead on local developer/user systems. Lexical FTS5 provides instantaneous, robust performance in a lightweight package.
* **External Third-Party RAG SaaS integrations**: System remains 100% local and private.

---

## Risk Classification

### Risk flags:
* **Data model**: Implementing SQLite FTS5 virtual tables and dynamic migrations.
* **Audit/security**: Prevention of SQL injection in dynamically generated FTS5 queries (using bind parameters).
* **Existing behavior**: Intercepting and replacing the current `TAX_REGULATIONS` static arrays.

### Hard gates:
* **Strict Non-blocking Startup**: Ingestion must run in a separate daemon thread to ensure the main Flask application boots instantly (under 0.5s).
* **No hardcoded credentials**: LLM provider API keys must leverage meInvoice's existing dynamic scheduler settings.

---

## Work Phases

### Phase 1: Discovery & Workspace Audit
* Verify `pypdf` parses layout structures in `luat48.pdf` correctly (Vietnamese Unicode encoding intact).
* Verify SQLite FTS5 extension is enabled by default in Python's standard library `sqlite3` on Windows.

### Phase 2: Structural & Schema Design
* Draft SQLAlchemy database models (`TaxRegulationChunk`, `AIChatSession`, `AIChatMessage`).
* Design SQLite triggers or programmatic synchronizers to mirror database writes into the FTS5 index.
* Layout premium CSS variables, glass styling classes, and fonts (Outfit & Inter) in `static/css/style.css`.

### Phase 3: Validation Planning
* Draft unit and integration tests under `tests/test_chatbot_rag_upgrade.py`.
* Establish deterministic mock queries (e.g. asking about "5 triệu" or "nông sản") and assert FTS5 returns exact articles.

### Phase 4: Implementation
* **Sprint 4.1 (Backend Data)**: Implement background daemon worker, PDF chunking pipeline, and DB indexer.
* **Sprint 4.2 (Search & Routing)**: Update `get_tax_rag_context` to perform dynamic SQLite search queries.
* **Sprint 4.3 (APIs & Memory)**: Build Chat Session REST endpoints and persistence layers.
* **Sprint 4.4 (Glassmorphic Front-End)**: Implement premium floating sidebar, custom scrollbars, styling variables, and Markdown table output.

### Phase 5: Verification & End-to-End Testing
* Run integration tests via `venv/Scripts/python -m pytest tests/test_chatbot_rag_upgrade.py`.
* Perform UI inspection to confirm responsive mobile rendering and smooth transition physics.

### Phase 6: Harness & Observatory Trace
* Log execution traces in Harness db.
* Mark story `US-CHATBOT-REGULATION-RAG-UPGRADE` as `implemented` in the query matrix.

---

## Stop Conditions

Pause execution and request manual human confirmation if:
1. **FTS5 Incompatibility**: Standard Windows Python installation lacks FTS5 SQLite compile flags (extremely rare, but requires falling back to standard LIKE indexing).
2. **LLM Timeout**: Ollama local query overhead exceeds 10 seconds per message, necessitating a client-side stream buffer implementation.
