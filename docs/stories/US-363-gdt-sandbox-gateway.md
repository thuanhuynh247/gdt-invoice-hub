# Story Specification: US-363 — Mock GDT Receiving Gateway Transmission Sandbox

## 📋 Context & Business Value
To test the e-invoice submission process end-to-end, developers need a mock GDT receiving gateway sandbox. This gateway acts as the GDT's server to receive signed XMLs, validate signatures and tags, and respond with mock GDT status codes.

---

## 🎯 Acceptance Criteria
- **GDT Sandbox Gateway**:
  - Expose a POST API endpoint `/api/gdt-sandbox/transmit` to receive signed XML files.
  - Parse and extract signature node details from the request payload.
  - Verify signature validity against intermediate and root CAs.
  - Return standard GDT response codes: `00` (Approved with code), `01` (Signature error), `02` (Invalid XML structure).

---

## 🛠️ Verification & Test Plan
- Run unit test verifying gateway transmission and responses:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v24_ocr_signing.py -k test_gdt_transmission_sandbox"
  ```
