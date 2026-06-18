# Compliance Swarm Orchestrator - Context

**Feature slug:** compliance_swarm_orchestrator
**Date:** 2026-06-18
**Exploring session:** complete
**Scope:** Standard
**Domain types:** SEE | CALL | RUN | ORGANIZE

## Feature Boundary

This feature implements the **Interactive Compliance & Swarm Audit Orchestrator UI** mounted at route `/compliance-swarm-dashboard`. It provides a premium dual-panel glassmorphic interface where users can trigger the multi-agent joint audit coordinator swarm (`JointAuditCoordinator`) with custom tax questions or taxpayer MST queries, view live animated message flows between agent nodes, inspect simulated real-time progress, and read/copy persistent audit reports and Decree 125/2020/NĐ-CP tax defense letter templates.

## Locked Decisions

These are fixed. Planning must implement them exactly.

- **D1 (UI/UX Architecture):** Implement a glassmorphic split-panel dashboard layout:
  - **Left Panel (Conversational & Reporting Workspace):** Contains a scrollable report zone displaying the synthesized Swarm Audit Report across tabs (e.g., "Overview", "Anomalies Log", "Decree 125 Defense Letter"), and a query box for triggering new audits.
  - **Right Panel (Interactive Agent Graph & Log Monitor):** Consists of an animated SVG network node graph representing the 4 swarm agents (Coordinator, AuditorAgent, ClassifierAgent, ForecasterAgent). During execution, visual pulsing gradient lines simulate message passes sequentially. Underneath the graph, a collapsible terminal-style log feed shows details.
- **D2 (Session Storage & Persistence):** Keep a history of swarm audit sessions. Create a SQLite table `swarm_audit_logs` inside the isolated tenant databases containing:
  - `session_id` (UUID or incremental ID)
  - `user_query` (Text input from query box)
  - `report_markdown` (Synthesized output report)
  - `swarm_confidence` (Float score between 0.0 and 1.0)
  - `created_at` (Timestamp)
  Provide a sidebar or dropdown to reload previous sessions.
- **D3 (Audit Defense Letter Interaction):** The tax defense template is displayed inside the left panel as a read-only markdown block equipped with a functional "Copy to Clipboard" utility button.
- **D4 (Sync/Async Execution Model):** The backend executes the swarm synchronously using the existing `JointAuditCoordinator.execute_swarm` flow. The frontend JS intercepts the response and replays the step-by-step agent activation animations with timed delays (e.g., 1.5 seconds per step transition) to deliver a simulated real-time experience without websocket complexity.

### Agent's Discretion

- The agent has discretion over CSS styling details, colors (must follow premium Wise HSL dark/light modes), SVG nodes positioning, and JS visual micro-interactions.
- The agent has discretion over standard HTML modal design for viewing/copying report components.

## Existing Code Context

### Reusable Assets

- `invoices/agent_swarm.py`: Defines `JointAuditCoordinator` and the specialized specialist agents.
- `invoices/routes/core.py`: Exposes `/api/agents/audit-coordinator` which coordinates the swarm synchronously.
- `static/css/style.css`: Contains CSS utility classes and design tokens.

### Established Patterns

- **Multi-tenant isolation:** Database connections must utilize `get_tenant_db_path(mst)` and run tenant-specific SQL scripts.
- **Wise Theme Design:** Clean borders, dark background variants, glowing box-shadows, and Inter typography.

### Integration Points

- `invoices/routes/core.py` (or a dedicated routes file): Mount the GET route `/compliance-swarm-dashboard` rendering `templates/compliance_swarm_dashboard.html`, and helper GET/POST API endpoints for history retrieval.
- `templates/base.html`: Include navigation links to the new dashboard.

## Canonical References

- [invoices/agent_swarm.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/agent_swarm.py) - Swarm logic.
- [invoices/routes/core.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes/core.py) - Swarm controller endpoint.

## Outstanding Questions

- None.

## Deferred Ideas

- WebSockets or Server-Sent Events for actual streaming. Deferred per **D4** in favor of simulated frontend replays.
