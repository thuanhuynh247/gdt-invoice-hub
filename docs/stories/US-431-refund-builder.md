# Story Specification: US-431 — Form 01/ĐNHT Refund Request Packet Builder & GDT XML Exporter

## 📋 Context & Business Value
To legally file for a VAT refund, taxpayers must compile Form 01/ĐNHT (Circular 80/2021/TT-BTC) and submit it electronically to the General Department of Taxation (GDT). The system must automatically build a compliant Form 01/ĐNHT XML package containing structural tags, bank credentials, refund reasons, and invoice/customs reconciliation arrays.

---

## 🎯 Acceptance Criteria
- **Form 01/ĐNHT XML Generator**:
  - Build a valid XML builder class/module for Form 01/ĐNHT in `invoices/refund_service.py` or `invoices/v32_service.py`.
  - Include tags: `<HSoKhaiThue>`, `<TTinDKT>`, `<TToanHT>`, `<CTietHoanThue>`, `<DSachHDonCustoms>`.
  - Populate banking information (Bank name, Branch, Account Holder, Account Number).
  - List matched customs declarations and purchase invoices inside the XML elements.
- **Export UI Controls**:
  - Enable downloading of the XML package with one click via `/api/reports/vat-refund/export-xml`.
  - Real-time XML structure preview inside the wizard with syntax-highlighted glass view.

---

## 🛠️ Verification & Test Plan
- Run validation tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v32_features.py"
  ```
