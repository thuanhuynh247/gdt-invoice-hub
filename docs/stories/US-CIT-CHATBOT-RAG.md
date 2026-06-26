# US-CIT-CHATBOT-RAG: Corporate Income Tax (CIT) 2025/2026 RAG Chatbot Integration

## 1. Description
Deepen the local chatbot's tax advisory capabilities by adding the new Corporate Income Tax (CIT) regulations (effective for tax periods 2025/2026) from the crawled/retrieved regulatory text (Văn bản hợp nhất số 61/VBHN-VPQH and Thông tư 20/2026/TT-BTC).

## 2. Requirements & Scope
- Compile the new CIT regulations text into a Vietnamese Tahoma-compatible PDF document `vanbanhopnhat61_2026_cit.pdf`.
- Parse, segment, and dynamically ingest PDF document chunks into the SQLite FTS5 table `tax_regulation_fts`.
- Update `parse_and_chunk_pdf` and ingestion pipelines to index CIT content with its proper effective date `2026-03-23`.
- Update fallback/static advisory dictionaries `TAX_REGULATION_EXCERPTS` (ai_tax_advisor.py) and `TAX_REGULATIONS` (ai_service.py) with the new CIT rules, tiered tax rates (15%, 17%, 20%), and Net Zero green transition / digital transformation allowances.
- Improve get_tax_rag_context to automatically perform loose term-level `OR` matching when exact phrase searches yield no matches.
- Create automated unit tests in `tests/test_cit_chatbot_rag.py` verifying full RAG matching.

## 3. Verification Criteria
- `tests/test_cit_chatbot_rag.py` must run and pass all 4 assertions.
- `tests/test_chatbot_rag_upgrade.py` must run and pass.
