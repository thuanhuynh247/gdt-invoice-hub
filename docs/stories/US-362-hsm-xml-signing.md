# Story Specification: US-362 — PKCS#11 HSM Cryptographic Signing Module

## 📋 Context & Business Value
Under Decree 123/2020/NĐ-CP, all e-invoices sent to the GDT must be digitally signed using a secure token or Hardware Security Module (HSM). The system needs a digital signing service to sign XML invoices using simulated PKCS#11 HSM certificates.

---

## 🎯 Acceptance Criteria
- **HSM XML Signature**:
  - Implement a cryptographic signing service using simulated X.509 certificates.
  - Calculate SHA-256 hash of XML data nodes.
  - Inject the signature node `<Signature>` (compliant with XMLDSig) into the invoice XML draft.
  - Verify that the signed XML matches the original data and has a valid digital signature.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying digital signature generation:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v24_ocr_signing.py -k test_hsm_signing"
  ```
