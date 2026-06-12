# US-720: Core Agricultural Land Use Tax Calculation Engine

## Story
**As a** tax compliance auditor,
**I want** to calculate Agricultural Land Use Tax (ALUT) based on land grade and crop type,
**So that** I can determine annual agricultural tax liabilities under Law on Agricultural Land Use Tax 1993.

## Acceptance Criteria
- Support annual crop land grades 1 to 6 (standard rates: 550, 460, 370, 280, 180, 50 kg rice/ha).
- Support perennial crop land grades 1 to 5 (standard rates: 650, 550, 400, 300, 200 kg rice/ha).
- Calculate paddy rice equivalent to VND based on current market price (e.g., 8,000 VND/kg).
- Save all calculations to the tenant database.
