# Story Specification: US-396 — Collaborative Swarm Chat Advisor & Simulation Panel

## 📋 Context & Business Value
Tax advisors and financial officers need a collaborative, multi-agent swarm discussion environment to prepare for tax audits. By simulating interaction among virtual specialized agents (Auditor, Classifier, Forecaster), users get a clear overview of compliance risks and optimization advice across domains.

---

## 🎯 Acceptance Criteria
- **Multi-Agent Simulation**:
  - Generate a step-by-step collaborative agent communication log (JointAuditCoordinator, AuditorAgent, ClassifierAgent, ForecasterAgent) discussing corporate tax risks.
- **Auditing Synthesis Report**:
  - Synthesize a comprehensive markdown report covering:
    - VAT & Decree 123 XML compliance warnings.
    - Decree 132 related-party transaction classification.
    - Treasury & VAT forecast analysis.
- **Endpoint Integration**:
  - Expose `/api/agents/swarm-chat` returning the step logs and final synthesis markdown report.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  venv\Scripts\python -m pytest tests/test_v28_features.py -k test_swarm_chat_advisor_simulation
  ```
