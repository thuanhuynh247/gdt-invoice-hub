# Story Specification: US-410 — Transfer Pricing & Arm's Length Transaction Analysis Engine

## 📋 Context & Business Value
Under Decree 132/2020/ND-CP, companies engaged in related-party transactions must ensure their transfer pricing profit margins (such as markup or operating margins) fall within the arm's length range (35th to 75th percentiles of independent benchmark companies in their sector). This engine automates markup auditing, risk classification, and projects tax adjustments and late-payment penalties if transactions are non-compliant.

---

## 🎯 Acceptance Criteria
- **Transfer Pricing Margins Calculator**:
  - Calculate Profit Markup or Operating Margin for related-party transactions.
  - Dynamically load sector benchmark ranges (e.g. Manufacturing, Services, Distribution) containing 35th percentile, Median (50th), and 75th percentile.
  - Classify compliance status: `Compliant` if within range, `Under-priced Risk` if below the 35th percentile, or `High-priced Risk` if above the 75th percentile.
  - If under-priced, calculate:
    1. Adjusted Taxable Income based on the benchmark median (50th percentile).
    2. Corporate Income Tax (CIT) underpayment (20% of adjustment).
    3. Underpayment penalty (20% of tax underpaid).
    4. Late payment interest (0.03% per day for a default period, e.g. 365 days).
  - Return a structured JSON compliance payload.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v30_features.py -k test_transfer_pricing_engine"
  ```
