# US-183 Dynamic Metadata Filter & Report Generator

## Status

implemented

## Lane

normal

## Product Contract

The application must provide a query builder interface allowing users to filter, group, and export invoice data based on custom schema extension tags stored inside the JSON metadata field.

## Relevant Product Docs

- `docs/product/v15_roadmap.md`

## Acceptance Criteria

- [x] Create search filter dropdowns that dynamically populate from registered schema extension fields.
- [x] Implement invoice list query filtering using JSON-extract functions on sqlite `metadata_json` column.
- [x] Provide analytical aggregation grouping invoice total amounts by dynamic tags (e.g. group by ProjectID).
- [x] Support exporting filtered reports (containing custom fields) to CSV and Excel.
- [x] Expose API endpoint `GET /api/schema/reports` to fetch filtered analytical aggregations.

## Design Notes

- **Module**: `invoices/schema_extensions.py` query builder.
- **SQL helper**: Utilizes SQLite's `json_extract(metadata_json, '$.[key]')` for efficient JSON querying.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v15_metadata_reporter.py` checking query builder JSON parsing and result grouping |
| Integration | Calling `/api/schema/reports` returns correct aggregated numbers and exports Excel with custom columns |
