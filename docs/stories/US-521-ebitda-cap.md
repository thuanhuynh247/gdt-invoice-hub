# Story US-521: Related-Party Transaction Detector & Decree 132 EBITDA Cap Auditor

## Title
Related-Party Transaction Detector & Decree 132 EBITDA Cap Auditor

## Description
Under Decree 132/2020/NĐ-CP, enterprises with related-party transactions (Giao dịch liên kết) face restriction on net interest expense deduction. Specifically, net interest expense (interest expense minus interest income) is limited to 30% of EBITDA. Disallowed interest is carried forward up to 5 consecutive years.
This story implements the engine to track related parties, calculate net interest expense, calculate company EBITDA, enforce the 30% limit, and calculate CIT taxable profit adjustments.

## Target Outputs
- Service method `RelatedPartyService.add_related_party_relationship(mst_a, mst_b, relationship_type, details)`
- Service method `RelatedPartyService.calculate_ebitda_limit(taxpayer_mst, year, profit_before_tax, interest_expense, interest_income, depreciation_amortization)`
- Return structured calculation result with fields: `ebitda`, `net_interest_expense`, `interest_cap`, `disallowed_interest`, `adjusted_taxable_profit`.

## Verification
- Unit test in `tests/test_v40_features.py`: `test_decree132_ebitda_cap()`.
