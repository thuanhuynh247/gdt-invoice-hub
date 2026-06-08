---
id: PRD-COMPLIANCE-E1-S1
type: story
epic: PRD-COMPLIANCE-E1
status: draft
lang: en
owner: Dev-Lead
version: 3.0.0
created: "2026-06-08"
updated: "2026-06-08"
personas:
  - "Tax Compliance Auditor"
scope: in
moscow: must
size: M
horizon: now
metrics:
  - "CIT adjustment calculation accuracy"
acceptance_criteria:
  - "Accurately classify compliance status: Compliant, Under-priced Risk, High-priced Risk based on sector benchmarks (manufacturing, services, distribution)."
  - "Calculate CIT adjustment up to the median (p50) of the sector range if under-priced."
  - "Compute 10% underpayment penalty on CIT underpayment."
  - "Calculate late payment interest using 0.03% daily rate for 365 days."
---

# Transfer Pricing Margin Calculations — Story PRD-COMPLIANCE-E1-S1

## User Story | Câu chuyện người dùng

**As a** Tax Compliance Auditor  
**I want** to calculate transfer pricing risk margins and penalty projections automatically  
**so that** I can project the potential corporate income tax adjustments and interest liabilities.

## Acceptance Criteria | Tiêu chí chấp nhận

* Compliant status: markup is inside p35 to p75 range. Risk score is 0, adjustments are 0.
* Under-priced Risk status: markup is below p35. CIT adjustment is computed to p50 (median) of the sector. Penalty is 10% of underpaid CIT. Late interest is 0.03% per day for 365 days.
* High-priced Risk status: markup is above p75. Risk score is 30, no direct CIT adjustment.
