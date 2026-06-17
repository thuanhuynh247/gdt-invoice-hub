# Spec: US-580 — Decree 123 E-Invoice Error Alerts & Form 04/SS-HĐĐT Status Tracker

## Status

completed

## Lane

normal

## Product Contract

The system provides an error notice status tracker and reporting log for Form 04/SS-HĐĐT under Decree 123/2020/NĐ-CP. It logs GDT feedback codes, tracks submission delays, and flags late filing warnings to prevent administrative tax penalties.

## Acceptance Criteria

- [x] Create `einvoice_incidents` and `form_04_ss_logs` tables in tenant databases.
- [x] Parse and log Form 04/SS-HĐĐT statuses (Accepted, Rejected, Pending).
- [x] Enforce filing deadlines: alert warning if Form 04/SS-HĐĐT is submitted after the last day of the subsequent month/quarter.
- [x] Save the audit warning indicators in the compliance ledger.

## Validation

- `tests/test_v46_features.py::test_einvoice_error_incidents`
