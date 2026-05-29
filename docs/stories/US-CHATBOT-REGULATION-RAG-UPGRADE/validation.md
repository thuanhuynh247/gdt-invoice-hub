# Validation Plan: Enterprise AI Chatbot RAG Upgrade (Dynamic Ingestion & Glassmorphic Chat UX)

## Proof Strategy

To verify the dynamic PDF-ingesting FTS5 Chatbot RAG upgrade, we utilize a comprehensive multi-layered validation strategy. Development is only declared **Done** when all tests are green and all structural contracts are validated.

---

## Test Plan

| Layer | Target Validation Cases | Expected Proof |
| --- | --- | --- |
| **Unit** | `test_pdf_text_extraction` | Verify `pypdf` extracts Vietnamese unicode text from `luat48.pdf` without corrupted bytes. |
| **Unit** | `test_text_splitter_paragraphs` | Verify parser splits text into chunks of 150–250 words, preserving page numbers and source mappings. |
| **Integration**| `test_database_migrations_exist` | Verify model schemas (`TaxRegulationChunk`, `AIChatSession`, `AIChatMessage`) migrate cleanly on DB startup. |
| **Integration**| `test_fts5_indexing_relevance` | Assert searching "nhà cung cấp nước ngoài" returns the specific chunk from `luat48.pdf` with the highest BM25 score. |
| **Integration**| `test_fts5_law_149_agriculture` | Assert searching "miễn thuế nông sản" or "500 triệu" matches the `luat149.signed.pdf` chunks with precision. |
| **Integration**| `test_chat_history_persistence` | Verify creating a session and adding three messages saves durably to SQLite, retrieving identically via GET. |
| **E2E / UI** | `test_glassmorphic_chat_drawer` | Verify CSS backdrop-filter styles and media queries render a responsive glassmorphic chat overlay. |
| **Performance**| `test_fts5_latency` | Assert FTS5 database lookup runs in under **5ms** on the target SQLite database. |

---

## Fixtures

Deterministic fixtures required for repeatable validation:
1. **Mock PDF Files**: Single-page PDFs with targeted keywords (`"luật 48"`, `"500 triệu"`) to verify chunking pipelines.
2. **Mock LLM Response Provider**: Mock Flask endpoint or patching utility simulating Ollama/Gemini API json formats:
   ```json
   {
     "message": {
       "content": "Căn cứ theo quy định mới..."
     }
   }
   ```
3. **Database Test Seed**: Programmatic script creating a clean temporary DB and populating taxpayer profiles for multi-session audits.

---

## Commands

Run tests using Python's virtual environment module executor to prevent import errors:

```bash
# 1. Run RAG and Search integration test suite
venv/Scripts/python -m pytest tests/test_chatbot_rag_upgrade.py -v

# 2. Run schema and database migrations tests
venv/Scripts/python -m pytest tests/test_db_migration.py -v

# 3. Complete project-wide validation checks
& "D:\Git\bin\bash.exe" scripts/harness validate --cmd "venv/Scripts/python -m pytest tests/test_chatbot_rag_upgrade.py"
```

---

## Acceptance Evidence

A final sign-off requires satisfying the following structural checks:
- [x] Ingestion worker spawns as a background daemon and logs status.
- [x] Database SQLite FTS5 table `tax_regulation_fts` is populated correctly.
- [x] REST API endpoints for chat sessions and history fetch successfully (HTTP 200).
- [x] Glassmorphic chat overlay renders without UI clipping on standard and mobile layouts.
- [x] Complete unit/integration test results logged to Harness DB traces.
