# Spec: US-481 — AI-Driven Loss Carry-Forward & Tax Holiday Optimizer

## Status
completed

## Lane
normal

## Product Contract

The system implements a **Loss Carry-Forward Optimizer** algorithm. It allows entering historical losses (up to 5 preceding years) and automatically offsets them against current and projected years, taking tax holidays into account to maximize overall tax savings.

## Acceptance Criteria

- [x] Optimization engine parses historical losses and calculates offset eligibility (max 5 years expiration).
- [x] Incorporates tax holiday settings (exemption / reduction) to avoid offsetting losses in 100% tax-free years where possible.
- [x] Provides API endpoint `/api/cit/optimize-losses` which returns the optimal carry-forward matrix.
- [x] Updates the dashboard dynamically when sliders or inputs are modified.
