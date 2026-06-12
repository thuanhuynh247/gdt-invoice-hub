# US-750: Core Environment Protection Fee for Mineral Extraction Engine

## Story
**As a** compliance manager,
**I want** to calculate environmental protection fees for mineral extraction based on raw material volumes and tariffs,
**So that** I can ensure regulatory compliance under Decree 27/2023/NĐ-CP.

## Acceptance Criteria
- Calculate mineral extraction fees based on raw materials and rates:
  - Crude Oil: 100,000 VND / tonne
  - Natural Gas & Coal Gas: 50 VND / m3
  - Associated Gas: 35 VND / m3
  - Stone (building materials): 7,500 VND / m3
  - Clay (brick/tile): 2,250 VND / m3
- Apply 60% rate (40% reduction) for salvage exploitation (khai thác tận thu) as prescribed by mining laws.
- Persist calculation inputs and results in the tenant-specific SQLite database.
