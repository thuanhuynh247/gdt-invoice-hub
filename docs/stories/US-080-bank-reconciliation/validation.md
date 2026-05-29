# Validation: US-080 & US-081 AI-Powered Multi-Source Bank Reconciliation

## Proof Strategy
Before marking the stories as implemented, we must run a strict validation suite verifying:
1. Bank statements are successfully parsed without memory leakages.
2. The fuzzy Soundex logic matches abbreviated bank description lines to corresponding taxpayer invoices.
3. API endpoints handle exceptions (such as duplicate uploads or negative amounts) securely.

---

## Test Plan

| Layer | Cases |
| --- | --- |
| **Unit** | `test_parse_vietcombank_statement_sheet` parses standard columns correctly. |
| **Unit** | `test_parse_techcombank_statement_sheet` parses customized references correctly. |
| **Unit** | `test_soundex_fuzzy_matcher_abbreviations` verifies that abbreviations match counterparts. |
| **Integration** | `test_auto_reconciliation_flow_api` uploads, maps, and executes auto-matching via REST. |
| **Edge Cases** | `test_duplicate_transaction_prevention` asserts reference numbers maintain uniqueness. |
| **Edge Cases** | `test_split_payment_matching` matches a transaction to multiple partial invoices safely. |

---

## Fixtures

### Sample Excel Columns Mapping (Vietcombank)
- **A**: Transaction Date (`2026-05-20`)
- **B**: Reference Number (`VCB-1299908882`)
- **C**: Debit Amount (Payments)
- **D**: Credit Amount (Receipts)
- **E**: Transfer Remarks (`CONG TY TOAN CAU CHUYEN KHOAN HD 1002`)

---

## Commands

Execute the newly developed test cases synchronously:
```bash
venv\Scripts\python -m pytest tests/test_bank_reconcile.py
```
