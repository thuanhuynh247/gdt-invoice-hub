# Spec: US-513 — Supplier Multi-Dimensional Risk Scorecard & SVG Network Graph

## Status

completed

## Lane

normal

## Product Contract

The system aggregates invoice compliance indicators to score supplier transaction security and renders a zero-dependency interactive SVG network graph representing supplier relationship risk.

## Acceptance Criteria

- [x] Computes supplier risk scores combining: MST blacklist status, invoice verification results, payment methods, and signing delays.
- [x] Renders a premium interactive SVG network graph in the web UI.
- [x] Node sizing corresponds to transaction value volume; node colors indicate risk level (Red: high, Yellow: medium, Green: low).
- [x] Responsive layout with support for hover highlighting and click events on nodes.

## Validation

- `tests/test_v39_features.py::test_supplier_network_graph`