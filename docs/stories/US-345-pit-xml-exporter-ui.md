# Story Specification: US-345 — PIT Finalizer & Form 05/QTT-TNCN UI

## 📋 Context & Business Value
To finalize personal income tax and prepare GDT filings, tax teams need a UI wizard that compiles year-end salary registers and exports the standardized Form 05/QTT-TNCN XML return.

---

## 🎯 Acceptance Criteria
- **Finalizer Wizard & Exporter**:
  - Provide a UI wizard displaying steps to finalize PIT (employee details, deduction inputs, PIT calculation summary).
  - Preview calculated data for BK05-1/BK05-2/BK05-3 components.
  - Export valid XML for Form 05/QTT-TNCN that is parsed by HTKK without error.
- **API Endpoint**:
  - `POST /api/payroll/export-pit-xml` compiling data and returning GDT-compliant Form 05/QTT-TNCN XML stream.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying Form 05/QTT-TNCN XML generation:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v22_payroll_pit.py"
  ```
