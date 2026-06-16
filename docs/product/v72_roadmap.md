# Version 72.0.0 Product Roadmap — Industrial Wastewater Surcharge Compliance Engine

This document defines the official product roadmap for **Version 72.0.0** of the GDT Invoice Hub. It implements the Industrial Wastewater Treatment Surcharge (Phí bảo vệ môi trường đối với nước thải công nghiệp) compliance engine under **Decree No. 53/2020/NĐ-CP**, providing tools to calculate environmental protection fees based on wastewater volume and pollutant concentration, and apply statutory exemptions.

---

## 🗺️ Product Timeline & Core Pillars

```mermaid
timeline
    title Invoice Webapp Roadmap (Version 72.0.0)
    section Pillar 1 — Core Wastewater Calculations (US-860)
        Base annual fee : US-860 1,500,000 VND / year (under 20 m3/day)
        COD variable charge : US-860 2,000 VND / kg
        TSS variable charge : US-860 4,000 VND / kg
        Heavy metal charges : US-860 Mercury (20M VND/kg), Lead (1M/kg), Cadmium (10M/kg)
    section Pillar 2 — Exemption Auditor (US-861)
        Cooling Water : US-861 100% exempt for clean cooling water loops without pollutant contact.
        Wastewater Treatment : US-861 100% exempt for municipal sewage/water treatment facility inflows.
        Double-counting check : US-861 Verify zero overlap with municipal drainage fees.
    section Pillar 3 — Interactive Dashboard UI & Tests (US-862 & US-863)
        Compliance Hub UI : US-862 Web console at `/v72-compliance-hub` with wastewater calculators and REST APIs.
        E2E Verification : US-863 End-to-end pytest verifying calculations, heavy metal rates, and APIs.
```

---

## 📋 Story Specifications Mapping

| Story ID | Name | Core Business Objective | Target Output Format |
| :--- | :--- | :--- | :--- |
| **US-860** | Core Industrial Wastewater Surcharge Engine | Calculate environmental protection fees for industrial wastewater based on COD, TSS, and heavy metals under Decree 53/2020/NĐ-CP. | Wastewater calculation ledgers |
| **US-861** | Wastewater Exemption Auditor | Verify fee exemptions for cooling water loops, clean water treatment, and municipal sewage fee overlap. | Wastewater exemption audit ledgers |
| **US-862** | Interactive Version 72 Compliance Hub UI and API | Provide a web dashboard at `/v72-compliance-hub` with wastewater calculators and REST APIs. | HTML Dashboard UI & REST JSON APIs |
| **US-863** | End-to-End V72 Verification Test Suite | Verify pollutant loading calculations, cooling water exemptions, municipal fee deductions, and API endpoints. | Pytest Suite (`tests/test_v72_features.py`) |

---

## ⚙️ Technical Constraints & Integration Guidelines

1. **Wastewater Fee Tariffs (US-860)**:
   - Base Fee: **1,500,000 VND / year** (flat fee for facilities discharging under 20 m3/day).
   - COD (Chemical Oxygen Demand) charge: **2,000 VND / kg**.
   - TSS (Total Suspended Solids) charge: **4,000 VND / kg**.
   - Mercury (Hg) charge: **20,000,000 VND / kg**.
   - Lead (Pb) charge: **1,000,000 VND / kg**.
   - Cadmium (Cd) charge: **10,000,000 VND / kg**.
2. **Exemptions (US-861)**:
   - Cooling water loops that discharge back to the environment with no pollutant contact → **100% exempt**.
   - Water treatment and municipal sanitary facilities → **100% exempt**.
   - Prevent double-counting: deductions applied for municipal drainage charges already paid.

---

## 🧪 Verification Plan

- Run validation wrapper:
   ```bash
   python scripts/harness_win.py validate --cmd "pytest tests/test_v72_features.py"
   ```
