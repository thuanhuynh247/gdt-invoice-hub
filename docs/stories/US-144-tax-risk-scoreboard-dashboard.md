# US-144 Tax Risk Scoreboard Dashboard

## Status

planned

## Lane

normal

## Product Contract

The application must aggregate and visualize VAT risk indicators (audit warning distributions, supplier risk ratings, total financial volume at risk) on a premium analytics scoreboard using inline dynamic SVGs styled with HSL variables.

## Relevant Product Docs

- `docs/product/v11_roadmap.md`

## Acceptance Criteria

- [ ] Add an API or query view collecting audit warning distribution counts (blacklist warnings, signature violations, payment type flags).
- [ ] Construct a modern SVG chart dashboard panel displaying warnings in a breakdown bar or pie chart.
- [ ] Group and list high-risk suppliers by total transaction value and warnings count.
- [ ] Verify that UI switches correctly between dark/light modes with HSL variable transitions.

## Design Notes

- **Aggregations**: Computed in database using SQLite queries across active taxpayer profiles.
- **Charts**: Custom generated SVGs for charts to ensure zero external dependency.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Verify aggregation query returns correct categories and counts |
| Integration | Verify dashboard UI elements render properly without JS errors |
