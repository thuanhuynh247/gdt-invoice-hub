# Story Specification: US-364 — Related Party Transaction Disclosure Checklist

## 📋 Context & Business Value
Under Decree 132/2020/NĐ-CP, companies must report transactions with related parties and declare them using Form 01/132. The system must automatically detect related parties and compute whether transaction values exceed reporting thresholds.

---

## 🎯 Acceptance Criteria
- **Related-Party Detection & Checklist**:
  - Scan the business partner database list.
  - Detect relationships conforming to Article 5 Decree 132 criteria (e.g., share ownership >= 25%, loans >= 50% of owner's equity).
  - Calculate total transactions with each related party during the fiscal period.
  - Determine if the reporting thresholds (Total Related-Party Transactions > 30B VND, or Total Revenue > 150B VND) are triggered.
  - Scaffolding fields for Form 01/132.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying related-party threshold calculations:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v24_transfer_pricing.py -k test_related_party_checklist"
  ```
