# Story Specification: US-360 — Physical Invoice Image OCR Pipeline

## 📋 Context & Business Value
To digitize physical or scanned invoices received as images (PNG, JPEG), the system needs a parsing service. This service processes the image to extract Seller MST, Buyer MST, Invoice Number, date, total amount, VAT amount, and confidence scores.

---

## 🎯 Acceptance Criteria
- **Image Upload & OCR Engine**:
  - Accept physical invoice image files (PNG/JPEG).
  - Extract the invoice date, Invoice Number, Seller MST, Buyer MST, Subtotal, VAT amount, and Grand Total.
  - Return extracted fields with confidence values.
  - Support fallback to a default mock/regex parser when OCR engines (like Tesseract) are not locally installed.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying OCR image parsing:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v24_ocr_signing.py -k test_ocr_pipeline"
  ```
