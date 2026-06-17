# Story Specification: US-394 — E-Contract XML Metadata Parser and Milestone Tracker

## 📋 Context & Business Value
To align sales and purchasing compliance with cash flows, the system needs to ingest structured electronic contract (Hợp đồng điện tử) details, parsing milestone values, signatures, and matching them to commercial invoices.

---

## 🎯 Acceptance Criteria
- **Contract Metadata Ingestion**:
  - Parse contracts XML/JSON structure, extracting fields: contract code (`SoHopDong`), contract date (`NgayKy`), total value (`GiaTriHopDong`), supplier name, customer name, and payment milestone logs (`DotThanhToan` containing due dates and percentage splits).
- **Invoice-Milestone Alignment**:
  - Reconcile invoice values and actual payment dates against the parsed milestone logs.
  - Flag overdue unpaid milestones or milestones invoiced with incorrect pricing.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v27_features.py -k test_econtract_milestone_parsing"
  ```
