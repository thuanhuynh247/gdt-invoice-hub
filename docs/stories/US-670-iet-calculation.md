# US-670: Core Import-Export Tax Calculation Engine

## Description
As a tax compliance system, I want to calculate import duties (preferential, ordinary, and special preferential) and export duties based on quantity and unit prices of goods under Law 107/2016/QH13, so that taxpayers can correctly assess their border duties.

## Acceptance Criteria
- Support calculation of export duties using standard (5%), mineral (10%), or agricultural (2%) rates.
- Support calculation of import duties using preferential/MFN (10%), ordinary (15%), or special preferential FTA (5%) rates.
- Save each calculation to the multi-tenant database under `iet_calculations` log table.
- Calculate total duty using the formula: `Duty = Quantity * Unit Price * Rate`.
