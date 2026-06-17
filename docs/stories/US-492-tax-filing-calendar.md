# Spec: US-492 — Comprehensive Tax Filing Calendar & Compliance Tracker

## Status
completed

## Lane
normal

## Product Contract

The system provides a **Tax Filing Calendar** UI component integrated into the CEO Dashboard, displaying all Vietnamese tax filing deadlines per Luật Quản lý Thuế 2019 (Law 38/2019/QH14) and Thông tư 80/2021/TT-BTC. Tracks filed vs pending status for each tax type/period, calculates a Tax Compliance Score, and pushes auto-reminder alerts (T-7, T-3, T-1 days) via Telegram and Email.

## Acceptance Criteria

- [x] Calendar view displays monthly deadlines for VAT, CIT quarterly, CIT annual, PIT annual, FCT.
- [x] Each deadline shows status: Filed ✅, Pending ⏳, Overdue 🔴.
- [x] Compliance Score computed as (on-time filings / total required filings × 100).
- [x] Auto-reminder alerts pushed at T-7, T-3, T-1 days before deadline via existing Telegram/Email integration.
- [x] API endpoint `/api/tax-planning/calendar` returns filing deadlines and status for a given fiscal year.
- [x] API endpoint `POST /api/tax-planning/calendar/mark-filed` updates filing status.
- [x] Database model `TaxFilingRecord` stores filing history.

## Validation

- `tests/test_v37_features.py::test_tax_calendar_deadline_computation`
- `tests/test_v37_features.py::test_tax_calendar_compliance_score`
- `tests/test_v37_features.py::test_tax_calendar_filing_status`
