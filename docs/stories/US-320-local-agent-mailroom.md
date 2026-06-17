# Story Specification: US-320 — Local Agent Mailroom & Coordination Hub

## 📋 Context & Business Value
To enable cooperative multi-agent tax audits, a secure local P2P message broker (Mailroom) is required to allow isolated specialized agents to exchange JSON payloads, log events, and coordinate tasks asynchronously.

---

## 🎯 Acceptance Criteria
- **Database Schema**: Extends DB schema with `AgentMessage` table representing sender, receiver, subject, payload, status, and timestamp.
- **REST Endpoints**:
  - `POST /api/agents/send` to dispatch messages to the mailbox queue.
  - `GET /api/agents/inbox/<agent_name>` to list pending or processed messages.
  - `POST /api/agents/update-status/<message_id>` to update status to processed/failed.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying DB persistence and API request routing:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_ai_swarm.py -k test_agent_mailroom_api"
  ```
