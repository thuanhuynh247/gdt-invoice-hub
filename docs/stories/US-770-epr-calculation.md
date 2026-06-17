# US-770: Core EPR Recycling Fee Engine

## Story
**As a** manufacturer or importer,
**I want** to calculate Extended Producer Responsibility (EPR) recycling fees for packaging and products,
**So that** I can ensure compliance under Decree 08/2022/NĐ-CP.

## Acceptance Criteria
- Calculate EPR contribution fee using formula: F = R * V * Fs.
- Support standard categories, rates (R), and coefficients (Fs):
  - Paper & Carton Packaging: R = 15%, Fs = 2,500 VND/kg
  - Plastic Packaging: R = 22%, Fs = 8,000 VND/kg
  - Metal Packaging: R = 20%, Fs = 4,000 VND/kg
  - Lead Acid Battery: R = 18%, Fs = 6,000 VND/kg
  - Lubricant Oil: R = 10%, Fs = 5,000 VND/kg
  - Electronic Appliances: R = 12%, Fs = 7,000 VND/kg
- Persist calculations in the tenant database.
