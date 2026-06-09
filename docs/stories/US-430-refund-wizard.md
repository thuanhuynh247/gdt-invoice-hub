# Story Specification: US-430 — Interactive Exporter VAT Refund Wizard with Glassmorphism Progress Metrics

## 📋 Context & Business Value
Export-oriented enterprises are eligible for VAT refunds under Vietnamese tax law (Circular 80/2021/TT-BTC) when they maintain compliant export structures, clear bank payment matches, and match relevant customs declarations. Tax practitioners need an interactive, user-friendly wizard dashboard to inspect eligible purchases, identify blocked invoices, match customs declarations, and trace refund eligibility rates with real-time feedback.

---

## 🎯 Acceptance Criteria
- **Multi-Step Glassmorphism Wizard UI**:
  - Render a premium UI panel for the exporter VAT refund workflow.
  - Step 1: **Profile & Bank Setup**: Select taxpayer MST, specify beneficiary bank name and account.
  - Step 2: **Purchase Eligibility Audit**: List purchase invoices, filter out cash transactions > 20M, missing signatures, or low trust scores.
  - Step 3: **Customs & Payment Reconciliation**: Pair exports with matching customs declarations and verify matching bank transactions.
  - Step 4: **Summary & Dossier Review**: View overall eligibility ratio and draft defense package.
- **Glassmorphism Metrics Dashboard**:
  - Show real-time progress indicators (eligibility ratio, total refund requested, and count of excluded invoices).
  - Clean responsive styling aligned with the system's luxury dark glass theme.

---

## 🛠️ Verification & Test Plan
- Run validation tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v32_features.py"
  ```
