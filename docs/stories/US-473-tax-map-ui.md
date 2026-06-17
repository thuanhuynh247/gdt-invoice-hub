# Spec: US-473 — Multi-Period Interactive Tax Map Explainer UI

## Status
completed

## Lane
normal

## Product Contract

The system provides an **Interactive Tax Map Explainer UI** displaying the flow of funds and tax calculations from initial business transactions to GDT forms (01/GTGT VAT, 03/TNDN CIT, 05/QTT-TNCN PIT). Visually links disallowed cost items from the audit engine to their respective tax form impact points.

## Acceptance Criteria

- [x] Web component renders dynamic SVG/HTML tax mapping visual showing fund tracing.
- [x] Tax map contains clickable nodes with live numeric tooltips showing details.
- [x] Connects disallowance events to related indicators, highlighting disallowance flow in red.
- [x] Zero-dependency CSS/SVG implementation for performance.
