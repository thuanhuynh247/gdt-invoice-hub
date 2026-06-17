# Spec: US-503 — AI Logistics Cost Allocation Engine (VAS 02)

## Status
completed

## Lane
normal

## Product Contract
The system provides a logistics cost allocation engine. It scans service invoices for freight, warehouse storage, customs, and transport fees, then auto-allocates those expenses to physical goods purchase invoices using date matching, vendor matching, and token-similarity keyword analysis.

## Acceptance Criteria
- [x] Parse and classify purchase invoices as logistics service invoices.
- [x] Match logistics invoices to physical goods purchase invoices using similarity thresholds.
- [x] Allow customizable allocation keys (Value-based, Quantity-based).
- [x] Persist allocation records in `LogisticsAllocation` database model.

## Validation
- `tests/test_v38_features.py::test_logistics_invoice_classification`
- `tests/test_v38_features.py::test_similarity_based_allocation`
