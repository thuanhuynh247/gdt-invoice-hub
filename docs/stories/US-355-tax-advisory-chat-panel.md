# Story Specification: US-355 — Advisory Chat & Defense Panel UI

## 📋 Context & Business Value
Users require a dedicated conversational interface within the GDT Invoice Hub to interact with the offline RAG system, draft audit defense letters, and review compliance citations.

---

## 🎯 Acceptance Criteria
- **Conversational Interface**:
  - Provide a chat interface in the dashboard for tax queries.
  - Render responses with formatted citations, laws, and regulations.
  - Implement a "Draft Defense Letter" tool that auto-fills details of invoice anomalies and formats a formal defense templates under Nghị định 125/2020/NĐ-CP.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying HTML templates and view endpoints:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v23_local_rag.py"
  ```
