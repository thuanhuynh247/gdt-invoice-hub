# Spec: US-474 — Enterprise Swarm Collaborative Audit Copilot

## Status
completed

## Lane
normal

## Product Contract

The system provides an **Enterprise Swarm Collaborative Audit Copilot** consisting of 4 AI agents (TaxInspector, TaxAdviser, CFO, LegalCounsel) debating tax compliance cases, showing conflicting view perspectives (tax auditor vs corporate defense), and outputting a draft justification defense letter.

## Acceptance Criteria

- [x] Simulates chat steps of multi-agent swarm debating audit issues.
- [x] TaxInspector agent raises challenges based on GDT rules and disallowances.
- [x] TaxAdviser, CFO, and LegalCounsel agents build arguments utilizing VAT/CIT codes.
- [x] Generates printable "Audit Defense Letter" in Markdown format.
- [x] API endpoint `/api/agents/swarm-v35-chat` executes swarm logic and returns steps.
