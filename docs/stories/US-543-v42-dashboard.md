# Spec: US-543 — Interactive Transfer Pricing & E-Commerce Audit Dashboard UI

## Status

planned

## Lane

normal

## Product Contract

A high-fidelity compliance dashboard page is rendered at `/v42-advanced-audit`. It contains an interactive SVG arm's length gauge, reconciliation cards, drag-and-drop platform file upload area, and a tax advisor swarm debate widget.

## Acceptance Criteria

- [ ] Add route `/v42-advanced-audit` in `invoices/routes.py` returning the dashboard template.
- [ ] Implement beautiful UI under the Cyber-Corporate Gold & Sapphire Blue theme.
- [ ] Draw an SVG Arm's Length range visualizer indicating whether the taxpayer's margin falls within the interquartile range.
- [ ] Include e-commerce reconciliation tables showing matched vs mismatched transactions and revenue gaps.
- [ ] Add the Swarm Debate Simulation panel displaying discussion transcripts from Tax personas.
- [ ] Provide endpoints to upload simulated e-commerce logs, generate XML exporter download, and query benchmarking comparator.

## Validation

- `tests/test_v42_features.py::test_v42_dashboard_endpoints`
