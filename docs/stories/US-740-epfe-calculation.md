# US-740: Core Environment Protection Fee for Emissions Engine

## Story
**As a** compliance manager,
**I want** to calculate environmental protection fees for industrial emissions based on fixed charges and pollutant loads,
**So that** I can ensure regulatory compliance under Decree 153/2024/NĐ-CP.

## Acceptance Criteria
- Calculate annual fixed emissions fee (3,000,000 VND/year, or 750,000 VND/quarter).
- Calculate variable emissions fees for facilities requiring monitoring based on pollutant weight:
  - Dust (Bụi): 800 VND/tonne (0.8 VND/kg)
  - NOx: 800 VND/tonne (0.8 VND/kg)
  - SOx: 700 VND/tonne (0.7 VND/kg)
  - CO: 500 VND/tonne (0.5 VND/kg)
- Persist calculation inputs and results in the tenant-specific SQLite database.
