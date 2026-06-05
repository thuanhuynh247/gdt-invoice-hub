# Story Specification: US-384 — Vietnamese Tax Law Knowledge Graph Constructor & Vector Store Indexer

## 📋 Context & Business Value
To empower tax audits with legal grounds and precision, the system will index key documents (Decree 123/2020, Circular 80/2021, Decree 132/2020) in a structured relational Knowledge Graph.

---

## 🎯 Acceptance Criteria
- **Knowledge Graph Model**:
  - Store articles, decrees, and circular provisions as nodes with specific tags, document names, section IDs, content body, and cross-reference links.
  - Expose API to perform structured query searches returning matching law nodes and their related citations.
- **Mock Vector Integration**:
  - Support query vector similarity mapping to find contextually relevant law nodes even if keywords are not exact matches.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest tests/test_v26_features.py"
  ```
