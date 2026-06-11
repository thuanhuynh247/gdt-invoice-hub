# Spec: US-534 — Export VAT Refund Compliance Dashboard & Timeline

## Status

planned

## Lane

normal

## Product Contract

The system renders an interactive compliance dashboard including non-cash bank payment status, customs clearance timelines, and an interactive SVG roadmap timeline showing the stages of a VAT refund application.

## Acceptance Criteria

- [ ] Render a dashboard page with summary stats (cleared export value, pending refund amount, compliance rate).
- [ ] Render a zero-dependency SVG roadmap representing refund stages: Drafting -> Submission -> Customs check -> Payment check -> GDT Decision -> Refund Completed.
- [ ] Hovering over a node displays audit criteria and compliance checklist.
- [ ] Include quick-action button to trigger automatic non-cash proof verification.

## Validation

- `tests/test_v41_features.py::test_refund_dashboard_rendering`
