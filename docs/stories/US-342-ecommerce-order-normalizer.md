# Story Specification: US-342 — Shopee, Lazada & TikTok Shop Order Normalizer

## 📋 Context & Business Value
E-commerce sellers face complex reconciliation across Shopee, Lazada, and TikTok Shop. This story normalizes export transaction sheets from these platforms into a single unified database-friendly format.

---

## 🎯 Acceptance Criteria
- **Multi-Channel Normalization**:
  - Parse sales order feeds containing Order ID, transaction date, customer details, gross amount, and merchant platform fees.
  - Return standardized lists of orders.
- **API Endpoint**:
  - `POST /api/ecommerce/normalize-orders` uploading a CSV or passing JSON order details and returning a normalized schema.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying order parser:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v22_ecommerce.py"
  ```
