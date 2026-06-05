# Story Specification: US-383 — VietQR Dynamic Payment Slip Generator & Interactive Tax Payment Status Panel UI

## 📋 Context & Business Value
To speed up tax duty payments and reduce errors, the system must generate Napas 247 dynamic VietQR code strings/payloads based on outstanding ledger liabilities and display transaction details with a real-time simulated payment status panel.

---

## 🎯 Acceptance Criteria
- **VietQR Code Generator**:
  - Implement dynamic VietQR EMVCo generator that compiles tax code, amount, bank code, receiver name, and message details.
- **Payment Wizard UI**:
  - Interactive payment slip wizard showing the generated VietQR, payment amount, recipient info, and status indicator.
  - Interactive mock payment confirmation simulation changing state from `pending` to `paid` upon user action or API trigger.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest tests/test_v26_features.py"
  ```
