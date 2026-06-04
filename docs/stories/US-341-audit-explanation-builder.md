# Story Specification: US-341 — AI-Generated Audit Explanation & Defense Template Builder

## 📋 Context & Business Value
When audit risk alerts are generated, tax teams need to quickly draft formal explanations (Công văn giải trình) for tax authorities. This tool dynamically scaffolds compliant Vietnamese response letters citing statutory regulations.

---

## 🎯 Acceptance Criteria
- **Defense Drafting Engine**:
  - Automatically compose formal Vietnamese letters tailored to risks (e.g., related-party EBITDA cap, FCT withholding, customs VAT variance).
  - Quote valid statutory laws (e.g., Decree 125/2020/NĐ-CP, Decree 132/2020/NĐ-CP, Circular 103/2014/TT-BTC).
- **API Endpoint**:
  - `POST /api/audit/generate-explanation` returning structured markdown/text response letter.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying defense letter content:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v22_tax_audit.py"
  ```
