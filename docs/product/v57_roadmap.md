# Version 57.0.0 Product Roadmap — Registration Fee (RF) Compliance Engine

This document defines the official product roadmap and development specifications for **Version 57.0.0** of the GDT Invoice Hub. It implements the Registration Fee (Lệ phí trước bạ) compliance engine under **Nghị định 10/2022/NĐ-CP** and **Nghị định 20/2019/NĐ-CP**, providing tools to calculate registration fees for real estate, motor vehicles, motorcycles, yachts, and aircraft based on asset value and legislated rate schedules, and to audit for exemptions applicable to agriculture, diplomatic missions, and social-policy beneficiaries.

---

## 🗺️ Product Timeline & Core Pillars

```mermaid
timeline
    title Invoice Webapp Roadmap (Version 57.0.0)
    section Pillar 1 — Core RF Calculations (US-690)
        Land & Buildings : US-690 Registration fee at 0.5% of declared or GDT-appraised value for land-use rights and buildings/apartments.
        Motor Vehicles : US-690 Cars first-time registration: 2% (standard), up to 12% in Hanoi/HCMC; subsequent re-registrations: 2%. Motorbikes: 2%-5% by province.
        Watercraft & Aircraft : US-690 Yachts and aircraft: 1% of declared value.
        Calculation Engine : US-690 Dynamic database-backed ledger for storing asset registrations and calculated registration fees.
    section Pillar 2 — Exemption Auditor (US-691)
        Agricultural Land : US-691 Exempt 100% registration fee for land allocated for agricultural/forestry production.
        Diplomatic & Social : US-691 Exempt 100% for assets of foreign diplomatic missions, social-policy housing of revolutionary merit families.
        Transfer Within Family : US-691 Exempt 100% for agricultural land transferred within the same household.
    section Pillar 3 — Interactive Dashboard UI & Tests (US-692 & US-693)
        Compliance Hub UI : US-692 Web console at `/v57-compliance-hub` with real estate, vehicle, and watercraft RF calculators, log views, and simulated advisory debate.
        E2E Verification : US-693 End-to-end pytest verifying RF calculations, exemptions, and APIs.
```

---

## 📋 Story Specifications Mapping

| Story ID | Name | Core Business Objective | Target Output Format |
| :--- | :--- | :--- | :--- |
| **US-690** | Core Registration Fee Calculation Engine | Calculate registration fees for real estate (0.5%), motor vehicles (2%-12%), motorbikes (2%-5%), yachts/aircraft (1%) based on asset value and provincial rates. | RF calculation ledgers |
| **US-691** | RF Exemption Auditor | Verify exemptions for agricultural land, diplomatic assets, revolutionary merit family housing, and within-family agricultural transfers. | RF exemption audit ledgers |
| **US-692** | Interactive Version 57 Compliance Hub UI and API | Provide a web dashboard at `/v57-compliance-hub` containing RF calculators, logs, and REST JSON APIs. | HTML Dashboard UI & REST JSON APIs |
| **US-693** | End-to-End V57 Verification Test Suite | Verify RF rates, provincial surcharges, exemptions, dashboard routes, and database logs. | Pytest Suite (`tests/test_v57_features.py`) |

---

## ⚙️ Technical Constraints & Integration Guidelines

1. **Real Estate (US-690)**:
   - Land-use rights and buildings: **0.5%** of declared or GDT-appraised value.

2. **Motor Vehicles (US-690)**:
   - Cars — First-time registration (standard provinces): **2%** of GDT-appraised value.
   - Cars — First-time registration (Hanoi, HCMC): **12%** of GDT-appraised value.
   - Cars — Subsequent registrations: **2%** of GDT-appraised value.
   - Motorbikes — Cylinder capacity > 175cc: **5%** of value.
   - Motorbikes — Cylinder capacity ≤ 175cc: **2%** of value.

3. **Watercraft & Aircraft (US-690)**:
   - Yachts, motorboats, aircraft: **1%** of declared value.

4. **Exemptions (US-691)**:
   - Agricultural/forestry land allocated by the State → **100% exempt**.
   - Assets of foreign diplomatic missions/international organizations → **100% exempt**.
   - Social-policy housing for revolutionary merit families → **100% exempt**.
   - Agricultural land transferred within the same household → **100% exempt**.

---

## 🧪 Verification Plan

- Run validation wrapper:
   ```bash
   python scripts/harness_win.py validate --cmd "venv\Scripts\activate.bat && python -m pytest tests/test_v57_features.py"
   ```
