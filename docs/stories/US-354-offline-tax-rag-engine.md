# Story Specification: US-354 — Offline Ollama Tax Regulations RAG

## 📋 Context & Business Value
To answer complex corporate tax inquiries without sending sensitive local financial records to external third-party cloud APIs, the system requires an offline-capable Retrieval-Augmented Generation (RAG) engine connecting to a local Ollama service.

---

## 🎯 Acceptance Criteria
- **Ollama RAG Integration**:
  - Connect to Ollama API at `http://localhost:11434` with configurable model selection.
  - Implement a basic semantic search over locally indexed Vietnamese tax texts (Decree 123, Circular 80, Decree 125).
  - Prompt structure must guide the local model to cite specific Law, Decree, or Circular numbers in its reasoning.

---

## 🛠️ Verification & Test Plan
- Run unit test validating prompt formatting and mock connection responses:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v23_local_rag.py"
  ```
