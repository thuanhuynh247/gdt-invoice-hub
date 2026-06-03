# US-140 Immutable Security Audit Logger

## Status

implemented

## Lane

normal

## Product Contract

The application must include an isolated, tamper-proof activity logging database table/file capturing administrative and compliance events (such as session actions, taxpayer profile switcher triggers, data repairs, configuration updates, and manual invoice operations). The logging mechanism must be append-only and immutable to standard database mutations.

## Relevant Product Docs

- `docs/product/v11_roadmap.md`

## Acceptance Criteria

- [x] Create a `SecurityAuditLog` database model containing the following fields: timestamp, username, tax_code, event_category, ip_address, and event_details.
- [x] Implement an event listener or check preventing database updates or deletes on the `SecurityAuditLog` table.
- [x] Automatically write audit log entries on successful/failed authentication, taxpayer switching, configuration edits, XML data repairs, and invoice deletions.
- [x] Add unit tests verifying logger writes and database-level immutability enforcement.

## Design Notes

- **Model definition**: `SecurityAuditLog` in `invoices/models.py`.
- **Database enforcement**: Override SQLAlchemy query or implement events (`before_update`, `before_delete`) that raise an exception.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v11_audit_log.py` checks model integrity and write operations |
| Integration | Verify that actions (switcher, repairs, delete) trigger log writes |
