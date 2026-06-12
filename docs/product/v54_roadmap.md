# Version 54.0.0 Product Roadmap — Natural Resources Tax (NRT) Compliance Engine

This document defines the official product roadmap and development specifications for **Version 54.0.0** of the GDT Invoice Hub. It implements the Natural Resources Tax (NRT) compliance engine under **Luật Thuế tài nguyên 45/2009/QH12** as amended by **Luật 71/2014/QH13**, providing tools to calculate ad-valorem resource extraction taxes on minerals, water, timber, and marine products, and verify tax exemptions for natural water used in agriculture and hydropower below thresholds.

---

## 🗺️ Product Timeline & Core Pillars

```mermaid
timeline
    title Invoice Webapp Roadmap (Version 54.0.0)
    section Pillar 1 — Core NRT Calculations (US-660)
        Mineral Extraction Tax : US-660 Apply ad-valorem tax rates for metallic ores (iron 12%, copper 13%, gold 15%, tin 20%), non-metallic minerals (granite 8%, sand 7%, marble 9%).
        Water Resource Tax : US-660 Calculate NRT on surface water (1-3%) and groundwater (3-5%) extraction for industrial use.
        Timber & Forest Products : US-660 Calculate NRT on natural forest timber (10-35%) and plantation timber (1-5%).
        Marine Products : US-660 Calculate NRT on natural aquatic products (1-2%) and pearls/coral (6-10%).
    section Pillar 2 — Exemption & Threshold Auditor (US-661)
        Agricultural Water Exemption : US-661 Exempt natural water used directly for agriculture, forestry, fishery, and salt production.
        Small-Scale Hydropower Exemption : US-661 Exempt hydropower stations with installed capacity ≤ 2MW.
        Self-Consumed Resources : US-661 Audit resources extracted and consumed internally by mining enterprises vs. sold commercially.
    section Pillar 3 — Interactive Dashboard UI & Tests (US-662 & US-663)
        Compliance Hub UI : US-662 Web console at `/v54-compliance-hub` with NRT calculators, logs, and simulated advisory debate.
        E2E Verification : US-663 End-to-end pytest verifying NRT calculations, exemptions, and APIs.
```

---

## 📋 Story Specifications Mapping

| Story ID | Name | Core Business Objective | Target Output Format |
| :--- | :--- | :--- | :--- |
| **US-660** | Core Natural Resources Tax Calculation Engine | Classify and calculate NRT on minerals, water, timber, and marine products using ad-valorem percentage rates. | NRT calculation ledgers |
| **US-661** | NRT Exemption & Threshold Auditor | Audit exemptions for agricultural water, small-scale hydropower (≤ 2MW), and self-consumed resources. | NRT exemption audit ledgers |
| **US-662** | Interactive Version 54 Compliance Hub UI and API | Provide a web dashboard at `/v54-compliance-hub` containing NRT calculators, logs, and REST JSON APIs. | HTML Dashboard UI & REST JSON APIs |
| **US-663** | End-to-End V54 Verification Test Suite | Verify NRT rates, agricultural exemptions, hydropower thresholds, dashboard routes, and database logs. | Pytest Suite (`tests/test_v54_features.py`) |

---

## ⚙️ Technical Constraints & Integration Guidelines

1. **Core NRT Rates (US-660)**:
   - **Formula**: `NRT = Taxable Output Quantity × Unit Resource Price × Tax Rate (%)`
   - **Metallic Ores**: Iron ore 12%, Copper ore 13%, Gold ore 15%, Tin ore 20%.
   - **Non-Metallic Minerals**: Granite 8%, Sand 7%, Marble 9%, Limestone 5%.
   - **Water Resources**: Surface water 1-3% (industrial default 2%), Groundwater 3-5% (industrial default 4%).
   - **Natural Timber**: Natural forest timber 10-35% (hardwood default 25%), Plantation timber 1-5% (default 3%).
   - **Marine Products**: Natural aquatic products 1-2% (default 2%), Pearls/Coral 6-10% (default 8%).

2. **Exemption Audits (US-661)**:
   - **Agricultural Water**: Natural water used directly for agriculture, forestry, fishery, salt production → **100% exempt**.
   - **Small-Scale Hydropower**: Hydropower stations with installed capacity ≤ 2MW → **100% exempt**.
   - **Self-Consumed Resources**: Resources extracted and used internally (not sold) by the mining enterprise → taxed at **70% of the standard rate**.

---

## 🧪 Verification Plan

- Run validation wrapper:
   ```bash
   python scripts/harness_win.py validate --cmd "venv\Scripts\activate.bat && python -m pytest tests/test_v54_features.py"
   ```
