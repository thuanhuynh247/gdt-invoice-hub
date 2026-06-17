# Spec: US-471 — Dynamic Tax Audit Risk Stress Simulator Engine

## Status
completed

## Lane
normal

## Product Contract

The system provides a **Tax Audit Risk Stress Simulator Engine** allowing users to adjust dynamic variables (audit scan rate, auditor strictness level) via interactive sliders, projecting potential VAT/CIT disallowances, tax underpayment penalties (20%), and daily late payment interest (0.03% daily rate).

## Acceptance Criteria

- [x] Backend API endpoint `/api/compliance/stress-test` accepts taxpayer MST, scan rate (0.0 - 1.0), and strictness level ("lenient", "medium", "strict").
- [x] Computes underpayment penalties based on rule-based disallowances:
  - "lenient" -> only cash payment violations.
  - "medium" -> cash payments + late signing.
  - "strict" -> cash payments + late signing + blacklisted MSTs + TP markup violations.
- [x] Calculates late payment interest at 0.03% per day on the total tax underpaid for a baseline period.
- [x] Integrates with a visual control panel in the V35 dashboard.
