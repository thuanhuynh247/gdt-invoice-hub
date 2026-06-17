# Spec: US-501 — Reconciliation & Timing Penalty Advisor

## Status
completed

## Lane
normal

## Product Contract
The system tracks the elapsed days between the Electronic Delivery Note issuance date and the corresponding commercial invoice's signing date. If the delay exceeds 10 days (or legal bounds per Decree 123/2020/NĐ-CP), it alerts the user, computes potential administrative penalty ranges, and flags CIT deductibility risks.

## Acceptance Criteria
- [x] Calculate elapsed days between delivery note date and matched invoice signing date.
- [x] Flag overdue invoices that violate Decree 123/2020/NĐ-CP limits (e.g., > 10 days).
- [x] Estimate Vietnamese tax administrative penalty amounts.
- [x] Provide compliance warning summary cards.

## Validation
- `tests/test_v38_features.py::test_timing_penalty_calculations`
