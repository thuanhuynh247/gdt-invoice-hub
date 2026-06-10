# Spec: US-504 — Inventory Cost-Base Adjusted Valuation Report

## Status
completed

## Lane
normal

## Product Contract
The system compiles an inventory cost-base valuation report, adjusting inventory value to include allocated logistics/freight costs per VAS 02. Renders tabular view and prints/exports report.

## Acceptance Criteria
- [x] Calculate adjusted unit costs for inventory items including allocated freight.
- [x] Display comparison table of Original Cost vs. Adjusted Cost per VAS 02.
- [x] Export adjusted valuation report as PDF/Excel.

## Validation
- `tests/test_v38_features.py::test_inventory_valuation_adjustments`
