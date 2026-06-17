# US-690: Core Registration Fee Calculation Engine

## Story
**As a** tax compliance auditor,
**I want** to calculate registration fees for real estate, vehicles, motorbikes, yachts, and aircraft,
**So that** I can accurately determine the Lệ phí trước bạ obligation under Decree 10/2022/NĐ-CP.

## Acceptance Criteria
- Real estate registration fee calculated at 0.5% of declared/appraised value.
- Car first-time registration at 2% (standard) or 12% (Hanoi/HCMC).
- Car subsequent registration at 2%.
- Motorbike >175cc at 5%, ≤175cc at 2%.
- Yacht/aircraft at 1%.
- All calculations persisted to tenant database with audit trail.
