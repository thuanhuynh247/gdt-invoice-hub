# Story US-850: Core E-Waste Recycling & Disposal Fee Engine

## Business Need
Under Decree No. 08/2022/NĐ-CP (EPR framework in Vietnam), manufacturers and importers of electronics, batteries, and solar panels must calculate their recycling liabilities. If they do not perform self-recycling, they must pay recycling fees into the Vietnam Environment Protection Fund (VEPF).

## Technical Requirements
- Implement the core recycling fee calculation logic.
- Input: product category (`laptop`, `tv_monitor`, `phone`, `battery`, `solar_panel`), count/quantity (units or kg).
- Rates:
  - `laptop` (Laptops & PCs): **20,000 VND / unit**
  - `tv_monitor` (TVs & Monitors): **30,000 VND / unit**
  - `phone` (Mobile Phones): **5,000 VND / unit**
  - `battery` (Lead-Acid Batteries): **50,000 VND / kg**
  - `solar_panel` (Solar Panels): **15,000 VND / kg**

## Acceptance Criteria
- Correct fee computation for all five categories.
- Reject negative values or invalid categories with clear validation errors.
- Result payload must include gross fee, category-specific rates, and metadata.
