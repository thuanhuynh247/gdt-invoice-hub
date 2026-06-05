# Story Specification: US-353 — ERP Webhook Dispatcher & Registry

## 📋 Context & Business Value
ERPs need real-time notifications about invoice changes, GDT risk score updates, or compliance warnings to avoid poll-based overhead and keep their internal ledger synchronized.

---

## 🎯 Acceptance Criteria
- **Webhook Dispatcher**:
  - Implement registration routes enabling users to subscribe webhook endpoints to specific events (e.g. `invoice.created`, `risk.score_high`).
  - Dispatch event payloads asynchronously with signature validation.
  - Implement a retry queue utilizing exponential backoff (up to 5 retries) and logging delivery attempts.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying dispatch, retry logic, and webhook event logs:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v23_api_gateway.py"
  ```
