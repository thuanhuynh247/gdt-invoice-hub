# US-154 Cross-Tenant Consolidated Dashboard

## Status

planned

## Lane

high_risk

## Product Contract

The application must provide a parent-tenant consolidation view aggregating financial statistics (total revenue, VAT input/output, average T-scores, invoice counts) across all authorized taxpayer profiles within a corporate group. Access must be restricted by role-based authorization ensuring data isolation between unrelated tenants.

## Relevant Product Docs

- `docs/product/v12_roadmap.md`

## Acceptance Criteria

- [ ] Implement data model linking parent-entity accounts to authorized sub-entity MSTs.
- [ ] Create API endpoint `GET /api/tenant/consolidated` returning aggregated multi-entity statistics.
- [ ] Build a premium Glassmorphism dashboard panel displaying group-wide KPIs with entity-level drill-down.
- [ ] Enforce role-based access control — only Group Admin accounts can access the consolidated view.
- [ ] Allow filtering and sorting by entity name, MST code, and date ranges.
- [ ] Write integration tests verifying data isolation (tenant A cannot see tenant B's data).

## Design Notes

- **Authorization model**: New `TenantGroup` association table in `invoices/models.py`.
- **Aggregation**: Server-side SQLite UNION queries across tenant databases.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Verify aggregation queries return correct sums across mock tenants |
| Integration | Verify role-based access denies unauthorized cross-tenant access |
