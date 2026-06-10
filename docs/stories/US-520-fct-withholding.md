# Story US-520: FCT (Foreign Contractor Tax) Auditing & Form 01/NTNN Calculation Engine

## Title
FCT (Foreign Contractor Tax) Auditing & Form 01/NTNN Calculation Engine

## Description
Under Circular 103/2014/TT-BTC, payments to foreign vendors/contractors who conduct business in Vietnam or derive income from Vietnam are subject to withholding tax (VAT and CIT components).
This story implements the engine to calculate withholding taxes for Gross and Net contract scenarios, suggest accounting journal entries, and generate the structured FCT declaration data (Form 01/NTNN).

## Target Outputs
- Service method `FCTService.calculate_fct_withholding(contract_value, contract_type, service_category)`
- Service method `FCTService.generate_fct_declaration(taxpayer_mst, period)`
- Return structured calculation result with fields: `contract_value`, `contract_type`, `service_category`, `fct_vat_rate`, `fct_cit_rate`, `taxable_revenue_vat`, `taxable_revenue_cit`, `fct_vat_amount`, `fct_cit_amount`, `total_fct_withheld`, `suggested_journal_entries`.

## FCT Rates (Circular 103/2014/TT-BTC)
- **goods_supply**: VAT: Exempt (0%), CIT: 1%
- **services**: VAT: 5%, CIT: 5%
- **technical_services**: VAT: 5%, CIT: 5%
- **software_royalty**: VAT: Exempt (0%), CIT: 10%
- **construction_with_materials**: VAT: 3%, CIT: 2%
- **construction_without_materials**: VAT: 5%, CIT: 2%

## Verification
- Unit test in `tests/test_v40_features.py`: `test_fct_withholding_calculation()`.
