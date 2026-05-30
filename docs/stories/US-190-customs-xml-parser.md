# US-190 Customs XML Parser & Import-Export Duty Calculator

## Status

planned

## Lane

normal

## Product Contract

The application must provide a parser engine for Vietnam Customs XML declaration documents (Tờ khai hải quan), extracting import-export value, exchange rates, and recalculating import duties, export duties, and import VAT based on statutory tax formulas.

## Relevant Product Docs

- `docs/product/v16_roadmap.md`

## Acceptance Criteria

- [ ] Build a parser that extracts metadata (Customs Declaration ID, Date, Incoterms, Currency, Exchange Rate, Total Value, Products list) from VNACCS/VCIS Customs XML files.
- [ ] Implement tax calculation logic for import duties, export duties, anti-dumping duties, and import VAT.
- [ ] Provide a frontend panel to upload customs XML files, view item lists, and inspect recalculated tax breakdowns.
- [ ] Expose API endpoint `POST /api/customs/parse` to process and return calculation metrics.
- [ ] Write unit tests validating parsing accuracy and mathematical correctness of tax calculations.

## Design Notes

- **Module**: `invoices/customs_parser.py`
- **Data storage**: Saves parsed declaration profiles in `instance/customs_declarations.json` or taxpayer database.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v16_customs_parser.py` verifying customs declaration parsing and recalculation math |
| Integration | API endpoint `POST /api/customs/parse` parses a sample VNACCS XML and returns correct VAT/Duty details |
