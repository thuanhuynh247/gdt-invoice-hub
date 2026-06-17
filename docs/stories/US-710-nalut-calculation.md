# US-710: Core Non-Agricultural Land Use Tax Engine

## Story
**As a** tax compliance auditor,
**I want** to calculate NALUT for residential, commercial, production, and idle land,
**So that** I can determine annual land use tax obligations under Law 48/2010/QH12.

## Acceptance Criteria
- Residential land tiered: 0.03% (≤ quota), 0.07% (1x-3x), 0.15% (> 3x).
- Commercial and production: flat 0.03%.
- Idle land: 0.03% + 0.02%/year surcharge, capped at 0.15%.
- All calculations persisted to tenant database.
