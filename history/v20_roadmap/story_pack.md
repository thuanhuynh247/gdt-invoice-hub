# Current Story Pack: US-320 - Local Agent Mailroom & Coordination Hub

## Context & Alignment
- **Epic**: Epic E91: Tax AI Agent Swarm (Harness v2.0-aligned)
- **Story ID**: `US-320`
- **Objective**: Create the SQLite schema for local P2P agent communications (AgentInbox, AgentOutbox), expose Python APIs for agent message dispatch/retrieve, and write basic tests checking P2P integration.

---

## 🚪 Entry State
- There is no message broker or database table to support communication between local agents in the workspace.
- The `invoices` module does not have a routing system or mailbox framework for cooperative multi-agent execution.

---

## 🏁 Exit State
1. **Database Schema Extension**:
   - `AgentMessage` model in `invoices/models.py` has fields: `id` (primary key), `sender_agent` (string), `receiver_agent` (string), `subject` (string), `payload` (JSON text), `status` (string: pending/processed), `timestamp` (DateTime).
2. **API Endpoints**:
   - `POST /api/agents/send` to publish a message from one agent to another.
   - `GET /api/agents/inbox/<agent_name>` to list messages waiting for a specific agent.
3. **Validation Tests**:
   - A new test suite `tests/test_ai_swarm.py` is written to verify agent P2P message posting, retrieval, and state marking.

---

## 📂 Files Likely Touched
- `invoices/models.py`
- `invoices/routes.py`
- `tests/test_ai_swarm.py` (New test file)

---

## 🔍 Feasibility Assumptions & Risk Mitigations
- **Assumption 1**: SQLite JSON operations can store dynamic payloads cleanly.
  - *Mitigation*: Store the payload as a stringified JSON field, using python `json.dumps`/`json.loads` on retrieval.

---

## 🧪 Verification Plan
- **Preflight & Compilation**:
  - Run compile check to verify syntax: `venv\Scripts\python.exe -m compileall invoices\models.py invoices\routes.py`
- **Tests Execution**:
  - Run new unit tests: `venv\Scripts\python.exe -m pytest tests/test_ai_swarm.py -v`

---

## 🛑 Out of Scope
- Autonomous Joint Audit Coordinator (`US-321`) which coordinates actual user prompts.
- Frontend graphical screens for inspecting the swarm's mail logs.
