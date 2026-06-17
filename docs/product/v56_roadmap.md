# Version 56.0.0 Product Roadmap — License Fee (LF) Compliance Engine

This document defines the official product roadmap and development specifications for **Version 56.0.0** of the GDT Invoice Hub. It implements the License Fee (LF) compliance engine under **Nghị định 139/2016/NĐ-CP** (Lệ phí môn bài), providing tools to calculate license fees for enterprises and households based on charter capital and revenue brackets, and check for operational, agricultural, or revenue-based exemptions.

---

## 🗺️ Product Timeline & Core Pillars

```mermaid
timeline
    title Invoice Webapp Roadmap (Version 56.0.0)
    section Pillar 1 — Core LF Calculations (US-680)
        Enterprise Brackets : US-680 Brackets based on Charter Capital (Vốn điều lệ) (> 10B: 3,000,000 VND/year; ≤ 10B: 2,000,000 VND/year; Branches/RO: 1,000,000 VND/year).
        Household Brackets : US-680 Brackets based on annual revenue (> 500M: 1,000,000 VND/year; 300M-500M: 500,000 VND/year; 100M-300M: 300,000 VND/year).
        Calculation Engine : US-680 Dynamic database-backed ledger for storing tax entities and calculated license fees.
    section Pillar 2 — Exemption Auditor (US-681)
        Low Revenue Exemption : US-681 Exempt 100% of households/individuals with annual revenue ≤ 100 million VND.
        First-Year Exemption : US-681 Exempt 100% of newly established enterprises/households in their first calendar year of operation.
        Agri Cooperatives : US-681 Exempt 100% of cooperatives engaged in agricultural production.
    section Pillar 3 — Interactive Dashboard UI & Tests (US-682 & US-683)
        Compliance Hub UI : US-682 Web console at `/v56-compliance-hub` with enterprise and household LF calculators, log views, and simulated advisory debate.
        E2E Verification : US-683 End-to-end pytest verifying LF calculations, exemptions, and APIs.
```

---

## 📋 Story Specifications Mapping

| Story ID | Name | Core Business Objective | Target Output Format |
| :--- | :--- | :--- | :--- |
| **US-680** | Core License Fee Calculation Engine | Calculate license fees for enterprises based on charter capital and branches, and for households/individuals based on revenue. | LF calculation ledgers |
| **US-681** | LF Exemption Auditor | Verify exemptions for low revenue (≤ 100M VND), newly established first-year businesses, and agricultural cooperatives. | LF exemption audit ledgers |
| **US-682** | Interactive Version 56 Compliance Hub UI and API | Provide a web dashboard at `/v56-compliance-hub` containing LF calculators, logs, and REST JSON APIs. | HTML Dashboard UI & REST JSON APIs |
| **US-683** | End-to-End V56 Verification Test Suite | Verify LF rates, branch aggregations, exemptions, dashboard routes, and database logs. | Pytest Suite (`tests/test_v56_features.py`) |

---

## ⚙️ Technical Constraints & Integration Guidelines

1. **Enterprise Brackets (US-680)**:
   - Charter Capital > 10 Billion VND: **3,000,000 VND/year**
   - Charter Capital ≤ 10 Billion VND: **2,000,000 VND/year**
   - Branches, Representative Offices, Business Locations: **1,000,000 VND/year** each.

2. **Household/Individual Brackets (US-680)**:
   - Revenue > 500 Million VND/year: **1,000,000 VND/year**
   - Revenue from 300 to 500 Million VND/year: **500,000 VND/year**
   - Revenue from 100 to 300 Million VND/year: **300,000 VND/year**

3. **Exemptions (US-681)**:
   - Annual Revenue ≤ 100 Million VND → **100% exempt**.
   - Newly established enterprises, households, or individuals starting business for the first year (established in current year) → **100% exempt**.
   - Cooperatives engaged in agricultural production → **100% exempt**.

---

## 🧪 Verification Plan

- Run validation wrapper:
   ```bash
   python scripts/harness_win.py validate --cmd "venv\Scripts\activate.bat && python -m pytest tests/test_v56_features.py"
   ```
