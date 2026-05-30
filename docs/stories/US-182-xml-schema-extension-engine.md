# US-182 Schema Extension Engine for Custom Fields

## Status

planned

## Lane

normal

## Product Contract

The application must support a flexible schema extension engine enabling users to define custom XML metadata tags (e.g. ProjectID, VehicleNumber), parse them from uploaded invoice XML files, and persist them dynamically into a JSON metadata field in the invoice database.

## Relevant Product Docs

- `docs/product/v15_roadmap.md`

## Acceptance Criteria

- [ ] Provide a schema builder settings UI to define custom metadata field mappings (XML path, field name, data type).
- [ ] Implement XML parser updates to dynamically extract defined custom tags.
- [ ] Save custom metadata tags as a JSON object in the `metadata_json` column of the `Invoice` table.
- [ ] Expose API endpoint `POST /api/schema/extensions` to register new custom fields.
- [ ] Write unit tests verifying custom tag extraction from standard GDT XML files with extended elements.

## Design Notes

- **Module**: `invoices/schema_extensions.py`
- **Database modification**: The `Invoice` table utilizes its JSON column `metadata_json` (added or existing) to store the dynamic key-value pairs without changing sqlite schema columns.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v15_schema_extensions.py` verifying dynamic XML parsing and extraction of custom tags |
| Integration | Uploading an XML with custom tags correctly saves the key-value pairs in the database's JSON metadata field |
