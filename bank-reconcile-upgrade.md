# Bank Ingestion & NLP Reconciliation Engine Upgrade

## Goal
Enhance the GDT Invoice Hub bank statement ingestion to support bank-specific formats (Vietcombank, Techcombank, BIDV) and implement Jaro-Winkler string similarity matching for high-precision auto-reconciliation and non-cash payment compliance checks.

## Affected Files
- `invoices/bank_reconcile_service.py`: Update parsing logic, add Jaro-Winkler, improve matcher.
- `tests/test_bank_reconcile.py`: Add unit tests for bank-specific parsing and Jaro-Winkler matching.

## Tasks
- [x] Task 1: Add pure Python `jaro_winkler_similarity` function to `invoices/bank_reconcile_service.py` -> Verify: Run manual tests checking string similarities.
- [x] Task 2: Enhance `_map_row_to_tx_dict` to recognize bank-specific headers for Vietcombank, Techcombank, and BIDV -> Verify: Check parsing maps expected debit/credit amounts and transaction descriptions.
- [x] Task 3: Upgrade `find_matching_invoice` to leverage Jaro-Winkler similarity on company buyer/seller tokens -> Verify: Fuzzy-match descriptions containing abbreviated partner names with invoices.
- [x] Task 4: Run the test suite via Pytest -> Verify: Confirm all tests (including new bank statement test cases) pass successfully.

## Done When
- [x] Jaro-Winkler similarity is fully functional and used to match partner names.
- [x] Excel/CSV bank statement parsed fields map correctly for VCB, TCB, and BIDV.
- [x] Pytest test suite runs and passes with 100% success rate.
