# Spec: US-562 — Interactive Version 44 Compliance Hub UI and API

## Status

planned

## Lane

normal

## Product Contract

The system provides a unified Compliance Hub UI page at `/v44-compliance-hub` and associated API endpoints to run Decree 123 VAT Adjustment reconciliations, model Science & Tech Fund allocations, simulate clawbacks, and visualize compliance scores and risk warnings.

## Acceptance Criteria

- [ ] Register new route `/v44-compliance-hub` rendering a premium, interactive UI in `templates/v44_compliance_hub.html`.
- [ ] Implement REST API endpoints:
  - `/api/v44/reconcile-adjustments` (POST) to trigger Decree 123 adjustment reconciliations.
  - `/api/v44/sci-tech-fund/simulate` (POST) to run the 5-year timeline clawback and welfare fund simulation.
  - `/api/v44/compliance-data` (GET) to retrieve historical records, reconciliation alerts, and simulation matrices.
- [ ] Build a premium dashboard containing:
  - Decree 123 Adjustment Reconciliation report and mismatch warnings.
  - Interactive Sci-Tech Fund Simulator with slider controls for allocation percentage, annual R&D spend, and qualified vs non-qualified ratios.
  - Dynamic visual charts/progress-bars showing projected clawbacks and late interest penalties.
  - An AI-powered advisory panel displaying compliance debate highlights.

## Validation

- `tests/test_v44_features.py::test_v44_api_endpoints`
