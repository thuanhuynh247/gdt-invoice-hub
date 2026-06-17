# Story Specification: US-352 — Secure Versioned REST API Gateway

## 📋 Context & Business Value
To integrate the GDT Invoice Hub with corporate ERP systems (MISA, FAST, SAP, Odoo), external applications must be able to securely query invoices, risk scores, and ledger data via a secure, versioned API gateway.

---

## 🎯 Acceptance Criteria
- **Versioned API Routes**:
  - Expose versioned endpoint paths under `/api/v1/invoices` and `/api/v1/compliance-scores`.
  - Enforce HMAC-SHA256 signature verification computed over request metadata and body using shared API secrets.
  - Return standardized JSON error envelopes for unauthorized or invalid payloads.

---

## 🛠️ Verification & Test Plan
- Run unit test validating signature matching and gateway routes:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v23_api_gateway.py"
  ```
