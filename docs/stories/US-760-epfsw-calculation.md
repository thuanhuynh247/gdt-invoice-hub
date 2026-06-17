# US-760: Core Environment Protection Fee for Solid Waste Engine

## Story
**As a** compliance manager,
**I want** to calculate environmental protection fees for solid waste based on categories and volumes,
**So that** I can ensure regulatory compliance under Decree 164/2016/NĐ-CP.

## Acceptance Criteria
- Calculate solid waste fees based on categories and rates:
  - Hazardous solid waste: 100,000 VND / tonne
  - Ordinary industrial solid waste: 40,000 VND / tonne
  - Ordinary construction solid waste: 30,000 VND / tonne
  - Ordinary other solid waste: 20,000 VND / tonne
- Persist calculation inputs and results in the tenant-specific SQLite database.
