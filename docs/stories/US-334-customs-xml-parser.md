# Story Specification: US-334 — Customs XML Declaration Parser

## 📋 Context & Business Value
To handle imported goods audit trail, the app parses VNACCS/VCIS Customs import declaration XML formats, extracting HS codes, duties, VAT bases, and exchange rates.

---

## 🎯 Acceptance Criteria
- **Schema**: Map XML structure to `CustomsDeclaration` model.
- **Parsing Logic**: Extract HS codes, base currency values, net weight, duties, and import VAT payments.
- **API Endpoints**:
  - `POST /api/customs/upload` to upload and import declarations.
  - `GET /api/customs/declarations` to list imported declarations.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying customs XML parsing:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_customs_reconciler.py -k test_customs_declaration_ingestion"
  ```
