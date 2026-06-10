# Spec: US-512 — Cash-Flow Sensitivity Stress Simulator & Runway Gauge

## Status

completed

## Lane

normal

## Product Contract

The system simulates corporate cash runway based on current cash balance and adjustable collection/payment periods (DSO/DPO). Dragging parameters updates a dynamic, color-coded SVG runway progress gauge showing remaining months.

## Acceptance Criteria

- [x] Sliders in UI to modify Days Sales Outstanding (DSO) and Days Payable Outstanding (DPO) (0-90 days).
- [x] Backend simulation that computes Adjusted A/R, Adjusted A/P, net burn rate, and runway.
- [x] Visual SVG Runway Gauge that dynamically animates its progress and changes color (Green > 6m, Yellow 3-6m, Red < 3m).
- [x] Gracefully handles edge cases like division-by-zero (e.g. positive net flow / zero burn rate).

## Validation

- `tests/test_v39_features.py::test_cash_flow_stress_testing`