# US-161 Anomaly Alert Engine

## Status

planned

## Lane

normal

## Product Contract

The application must automatically scan newly imported invoices for risk anomalies (low T-Score, blacklisted sellers, signature mismatches) and generate persistent alert records with severity levels displayed via an alert bell icon on the navigation bar.

## Relevant Product Docs

- `docs/product/v13_roadmap.md`

## Acceptance Criteria

- [ ] Create `NotificationAlert` model with fields: timestamp, invoice_id, alert_type, severity, message, is_read.
- [ ] Hook into invoice import pipeline to trigger anomaly scanning automatically.
- [ ] Generate alerts for T-Score below configurable threshold (default < 50).
- [ ] Display alert bell icon with unread count badge in the navigation bar.
- [ ] Expose API `GET /api/notifications/alerts` with pagination and severity filter.
- [ ] Write tests verifying alert generation on import of risky invoices.

## Design Notes

- **Model**: `NotificationAlert` in `invoices/models.py`.
- **Hook point**: After `store_invoices()` in the import pipeline.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Verify alert creation for invoices below T-Score threshold |
| Integration | Verify API returns paginated alerts with correct severity |
