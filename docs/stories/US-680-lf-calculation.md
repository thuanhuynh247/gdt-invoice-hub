# US-680: Core License Fee Calculation Engine

## Description
As a tax manager, I want to calculate the annual license fee (lệ phí môn bài) for my company and household branches based on charter capital and revenue brackets under Decree 139/2016/NĐ-CP.

## Acceptance Criteria
- Enterprise brackets based on Charter Capital:
  - > 10 Billion VND: 3,000,000 VND/year.
  - ≤ 10 Billion VND: 2,000,000 VND/year.
  - Branches/Rep Offices/Business locations: 1,000,000 VND/year.
- Household/Individual brackets based on annual revenue:
  - > 500 Million VND: 1,000,000 VND/year.
  - 300 Million to 500 Million VND: 500,000 VND/year.
  - 100 Million to 300 Million VND: 300,000 VND/year.
- Save calculations to the multitenant SQLite database under `lf_calculations` table.
