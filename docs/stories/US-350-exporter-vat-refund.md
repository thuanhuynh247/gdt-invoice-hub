# Story Specification: US-350 — Input VAT Evaluator Engine

## 📋 Context & Business Value
To automate the preparation of exporter VAT refund packages, the system requires a tax compliance evaluator that automatically audits input VAT invoices against GDT rules and Circular 80/2021/TT-BTC constraints.

---

## 🎯 Acceptance Criteria
- **Input VAT Audit Engine**:
  - Implement a check to verify supplier tax codes (MST) are active.
  - Automatically flag input invoices > 20M VND that lack corresponding bank payment matching records.
  - Verify match between customs declarations (Tờ khai Hải quan) and export invoices based on product description, quantity, and currency value.
- **API Endpoint**:
  - `POST /api/audit/vat-refund-eligibility` receiving list of input invoice IDs and customs declarations, returning an eligibility evaluation report with warnings and passing statuses.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying eligibility evaluation logic:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v23_vat_refund.py"
  ```
