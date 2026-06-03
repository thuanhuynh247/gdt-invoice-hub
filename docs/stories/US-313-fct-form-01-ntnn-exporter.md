# Story Specification: US-313 — FCT Form 01/NTNN Excel Exporter

## 📋 Context & Business Value
Withheld Foreign Contractor Tax must be declared to the tax authorities using Form 01/NTNN. To streamline this compliance reporting, this story automatically compiles the calculated FCT data into a standardized, audit-ready Excel sheet.

---

## 🎯 Acceptance Criteria

### 1. Declarant Data Compilation
- Compile period summary reports containing:
  - Total foreign contractor invoice counts.
  - Aggregated gross service values.
  - Total withheld VAT and CIT amounts.

### 2. Standardized Excel Structure
- Export compiled results to an Excel spreadsheet named according to the template format: `ToKhai_01NTNN_[YEAR]_[PERIOD].xlsx` (e.g. `ToKhai_01NTNN_2026_05.xlsx`).
- Set correct workbook headers, column titles, and borders.
- Include columns for:
  - Contractor Name
  - MST / Tax ID
  - Business Category
  - Contract Value
  - Withheld VAT rate & amount
  - Withheld CIT rate & amount
  - Total FCT due
- Response header must set `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

---

## 🛠️ Verification & Test Plan
- Run Pytest verification using `tests/test_fct_auditor.py`.
- Assert that calling `/api/reports/fct-declaration/export-excel` returns a valid Excel stream starting with zip binary bytes `PK\x03\x04`.
