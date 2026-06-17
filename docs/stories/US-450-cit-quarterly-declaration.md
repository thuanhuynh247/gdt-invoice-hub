# Spec: US-450 — CIT Quarterly Provisional Declaration Engine (Form 01A/TNDN XML Builder)

## Status
implemented

## Lane
high_risk

## Product Contract

The system shall provide a **CIT Quarterly Provisional Declaration Engine** that calculates corporate income tax (thuế TNDN tạm tính) on a quarterly basis and generates compliant Form 01A/TNDN XML. This enables enterprises to electronically file quarterly CIT estimated payments as required by Vietnamese tax law (Thông tư 80/2021/TT-BTC, Article 17).

## Acceptance Criteria

- [x] A service `invoices/v33_service.py` provides `calculate_cit_quarterly(taxpayer_mst, quarter, year, revenue, cogs, operating_expenses, other_income, other_expenses, preferential_rate)` returning a structured CIT calculation breakdown.
- [x] The engine computes: gross profit, operating income, taxable income, CIT payable (standard 20% or preferential rate), and carry-forward loss adjustment.
- [x] A function `build_form01a_tndn_xml(...)` generates HTKK-compatible XML for Form 01A/TNDN with all required fields (MST, company name, quarter/year, revenue breakdown, tax computation).
- [x] A function `get_tax_compliance_calendar(year)` returns a structured list of Vietnamese tax filing deadlines for VAT, CIT, PIT, FCT, and social insurance for the given year with status indicators.
- [x] API endpoint `POST /api/compliance/cit-quarterly` accepts quarter, year, and financial parameters and returns the CIT calculation.
- [x] API endpoint `POST /api/compliance/form01a-tndn-xml` generates and returns the Form 01A/TNDN XML.
- [x] API endpoint `GET /api/compliance/tax-calendar?year=YYYY` returns the compliance calendar.
- [x] Full test coverage in `tests/test_v33_features.py`.

## Design Notes

- **CIT Rate**: Standard 20%, with support for preferential rates (10%, 15%) per Nghị định 218/2013/NĐ-CP.
- **Loss Carry-Forward**: Up to 5 years per Article 9 Luật Thuế TNDN 14/2008/QH12.
- **Quarterly Filing Deadline**: Last day of the first month of the following quarter (e.g., Q1 due April 30).
- **XML Schema**: Follows HTKK Form 01A/TNDN structure with `<HSoThueDTu>` root element.
