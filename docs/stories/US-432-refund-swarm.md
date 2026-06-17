# Story Specification: US-432 — AI Swarm VAT Refund Justification Compiler & Multi-Agent Legal Defense Panel

## 📋 Context & Business Value
VAT refund claims are heavily audited by tax authorities. Taxpayers must present solid justification, matching contracts, customs files, and bank statements. An AI swarm comprising a Refund Auditor, a Customs Liaison, and a Tax Counsel can debate the compiled pack, flag missing declarations, reconcile transactions, and write a professional legal defense/justification letter citing Circular 80/2021/TT-BTC.

---

## 🎯 Acceptance Criteria
- **AI Refund Swarm**:
  - Run a 3-agent swarm chat process:
    - **RefundAuditor**: Focuses on cash compliance, signature checks, invoice T-scores.
    - **CustomsLiaison**: Reconciles customs declarations with sales invoice amounts and dates.
    - **TaxCounsel**: Generates the legal justification and defense letter draft referencing Decree 123/2020/NĐ-CP and Circular 80/2021/TT-BTC.
  - Compile chat logs and simulate/render them step-by-step on the UI.
- **Dossier & Justification Exporter**:
  - Render the final multi-page Justification Letter.
  - Provide export buttons to download as Word (`.doc`) and print-friendly PDF formats.

---

## 🛠️ Verification & Test Plan
- Run validation tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v32_features.py"
  ```
