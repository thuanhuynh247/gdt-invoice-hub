# Story Specification: US-321 — Autonomous Joint Audit Coordinator

## 📋 Context & Business Value
To perform comprehensive taxpayer audits, a coordinator orchestrates specialized agents (VAT, CIT, FCT, transfer pricing, and Customs) using the Agent Mailroom, ensuring complex auditing is delegated and results are compiled into a single consolidated report.

---

## 🎯 Acceptance Criteria
- **Coordinator Flow**:
  - Accept natural language query, analyze intent, and spawn sub-tasks.
  - Dispatch tasks via Agent Mailroom, wait for sub-agent results, and handle failure fallbacks.
  - Compile a unified HTML/Markdown audit report.
- **REST Endpoints**:
  - `POST /api/agents/audit-coordinator` to launch the joint audit swarm.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying swarm orchestration logic:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_ai_swarm.py -k test_joint_audit_coordinator_flow"
  ```
