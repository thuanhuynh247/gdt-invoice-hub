# Story Specification: US-361 — Automated XML Scaffold from Image OCR

## 📋 Context & Business Value
Once an invoice image is processed by the OCR pipeline, the system needs to generate a standardized, GDT-compliant e-invoice XML draft. This lets accounting users review, modify, and save the data without manual entry.

---

## 🎯 Acceptance Criteria
- **XML Scaffolding**:
  - Accept structured JSON from the OCR pipeline (US-360).
  - Scaffold a compliant General Department of Taxation (GDT) XML draft.
  - Structure must contain standard tag locations for `<HDon>` (Invoice), `<DLHDon>` (Data Content), `<TTChung>` (General Info), `<NDHDon>` (Invoice Content), and `<TToan>` (Payment details).
  - Support validation of the generated XML structure.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying XML scaffolding from OCR data:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v24_ocr_signing.py -k test_xml_scaffold"
  ```
