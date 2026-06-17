# Story Specification: US-351 — Form 01/ĐNHT Refund Packet Wizard

## 📋 Context & Business Value
Tax teams need a structured UI wizard to compile eligible input invoices, match them with export declarations, fill in Form 01/ĐNHT (Request for Tax Refund), and export GDT-compliant XML files for direct upload to GDT tax portals.

---

## 🎯 Acceptance Criteria
- **Refund Packet Wizard**:
  - Provide a step-by-step UI allowing users to select eligible input VAT invoices and link export/customs records.
  - Render an interactive preview of Form 01/ĐNHT.
  - Export a valid GDT-compliant XML file including refund parameters and voucher schedules.
- **API Endpoint**:
  - `POST /api/audit/export-refund-xml` returning the GDT-compliant XML stream representing Form 01/ĐNHT.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying XML schema generation:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v23_vat_refund.py"
  ```
