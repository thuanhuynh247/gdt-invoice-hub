# Story Specification: US-385 — Dynamic Audit Defense Document Composer & Socratic Advisory Panel UI

## 📋 Context & Business Value
When tax audits flag warning conditions (e.g., mismatching customs sheets, cash payments, or missing HSM certificates), companies must draft official defense/explanation documents. This story adds an advisor UI to compose standard-compliant responses using the indexed Knowledge Graph.

---

## 🎯 Acceptance Criteria
- **Advisory Questionnaire**:
  - Interactive questionnaire requesting user input on compliance contexts.
  - Socratic AI advisor that analyzes responses, updates the risk evaluation, and recommends optimal defense strategy.
- **Dynamic Letter Composer**:
  - Generate formatted response letters in printable HTML structure containing appropriate formal templates, GDT citation nodes, and explanations for audit flags.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest tests/test_v26_features.py"
  ```
