# US-700: Core Natural Resources Tax Calculation Engine

## Story
**As a** tax compliance auditor,
**I want** to calculate natural resources tax for minerals, petroleum, coal, water, timber, and marine products,
**So that** I can determine NRT obligations under Law 45/2009/QH12.

## Acceptance Criteria
- Metallic minerals taxed at 7%-25% based on mineral type.
- Non-metallic minerals taxed at 5%-15%.
- Crude oil sliding scale: ≤20k bbl/day at 6%, >20k at 10%.
- Natural gas at 2%, coal 5%-7%, water 3%, timber 15%-25%, marine 2%.
- All calculations persisted to tenant database with audit trail.
