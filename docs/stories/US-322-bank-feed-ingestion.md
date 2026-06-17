# Story Specification: US-322 — Bank Feed Ingestion & Transaction Normalizer

## 📋 Context & Business Value
To audit bank statement matches against invoices, the system must ingest ISO 20022 camt.053 XML statements and custom Vietnamese bank statement CSV formats (Vietcombank & Techcombank), normalizing them to a unified schema.

---

## 🎯 Acceptance Criteria
- **Schema**: Maps XML nodes and CSV columns to the `BankTransaction` table.
- **Parsing Engines**:
  - ISO 20022 parser handles `Ntry`, credit/debit indicators, and booking dates.
  - Vietcombank & Techcombank CSV parser correctly identifies dates, TxIDs, amounts, and transaction codes.
- **API Endpoint**:
  - `POST /api/bank/ingest` to import bank statements.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying bank feed ingestion and normalization:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_bank_matching.py -k test_bank_statement_ingestion"
  ```
