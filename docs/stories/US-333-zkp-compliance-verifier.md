# Story Specification: US-333 — Zero-Knowledge Proof Tax Compliance

## 📋 Context & Business Value
To verify corporate compliance with official VAT rate brackets without exposing confidential business transactions or item prices to external auditors, the system implements zero-knowledge proofs.

---

## 🎯 Acceptance Criteria
- **ZKP Logic**: Generate a proof file verifying the mathematical relation of before-tax amounts, VAT amounts, and standard brackets.
- **REST Endpoints**:
  - `POST /api/ledger/zkp-prove` to generate compliance proof.
  - `POST /api/ledger/zkp-verify` to cryptographically verify generated proof.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying proof creation and validation:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_cryptographic_ledger.py -k test_zkp_proving_and_verification"
  ```
