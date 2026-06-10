# Spec: US-474 — Enterprise Swarm Collaborative Audit Copilot

## Status
planned

## Lane
normal

## Product Contract

The system provides an **Enterprise Swarm Collaborative Audit Copilot** consisting of 4 AI agents (TaxInspector, TaxAdviser, CFO, LegalCounsel) debating tax compliance cases, showing conflicting view perspectives (tax auditor vs corporate defense), and outputting a draft justification defense letter.

## Acceptance Criteria

- [ ] Simulates chat steps of multi-agent swarm debating audit issues.
- [ ] TaxInspector agent raises challenges based on GDT rules and disallowances.
- [ ] TaxAdviser, CFO, and LegalCounsel agents build arguments utilizing VAT/CIT codes.
- [ ] Generates printable "Audit Defense Letter" in Markdown format.
- [ ] API endpoint `/api/agents/swarm-v35-chat` executes swarm logic and returns steps.
