# Validation

## Proof Strategy
We will implement automated tests mocking the Ollama / API connection endpoints. The test suite will verify database schema integrity, asynchronous audit triggering, prompt building correctness, structured response parsing, and UI badge rendering.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | - Verify prompt string builder compiles all line items correctly.<br>- Test structured JSON response parser against valid and corrupted LLM outputs. |
| Integration | - Mock AI API/Ollama server using `responses` or `unittest.mock`.<br>- Assert invoice audit triggers write corresponding warning rows to `ai_audit_results` table. |
| E2E | - Selenium flow: Log in, open Settings tab, configure mock AI connection, navigate to dashboard, trigger AI audit, and assert purple AI warning badge appears in Offcanvas drawer. |
| Performance | - Ensure LLM request timeouts (default 10s) prevent main Flask request thread blocking. |
| Logs/Audit | - Verify connection failures and parsing anomalies are logged with `warning`/`error` severity. |

## Fixtures
- Mock invoices containing items likely to be flagged:
  - `MOCK_INVOICE_ANOMALY_1`: contains line items like `"Điện thoại iPhone 15 Pro Max 512GB"` and `"Son môi dưỡng Dior"`.
  - `MOCK_INVOICE_ANOMALY_2`: contains line item `"Bút bi Thiên Long"` but with a unit price of `5,000,000 VND` (highly inflated).

## Commands
Run test suite:
```bash
venv\Scripts\pytest tests/test_ai_auditor.py
```
