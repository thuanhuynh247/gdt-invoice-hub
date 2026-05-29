# US-141 Audit Trail Viewer UI & Export

## Status

planned

## Lane

normal

## Product Contract

The application must provide a secure, user-friendly dashboard interface allowing administrators to view, search, and filter security audit logs, as well as export them to CSV and PDF formats for compliance and external auditing.

## Relevant Product Docs

- `docs/product/v11_roadmap.md`

## Acceptance Criteria

- [ ] Implement API endpoint `GET /api/audit/logs` returning paginated, filtered log records.
- [ ] Create a Glassmorphism-style UI tab in the settings/admin area displaying the logs in an interactive, responsive table.
- [ ] Add filters for date ranges, taxpayer MST profile, event categories, and keyword search.
- [ ] Implement export buttons to download filtered log views in CSV and PDF formats.
- [ ] Implement unit and integration tests covering the endpoint, filters, and export formatting.

## Design Notes

- **API route**: `/api/audit/logs` in `invoices/routes.py`.
- **UI page**: Integrated into base dashboard templates with proper access controls.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Test paginated logs API and query filters |
| Integration | Test CSV/PDF document generation and response headers |
