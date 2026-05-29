# US-165 Integration Marketplace & Webhook Registry

## Status

planned

## Lane

normal

## Product Contract

The application must provide a self-service integration management panel where administrators can register outbound webhook endpoints, configure event subscriptions, browse pre-built connector templates, and view delivery logs with retry history.

## Relevant Product Docs

- `docs/product/v13_roadmap.md`

## Acceptance Criteria

- [ ] Create `WebhookSubscription` model: url, events[], secret_key, is_active, created_at.
- [ ] Implement CRUD UI for webhook subscriptions in the settings panel.
- [ ] Support event types: `invoice.created`, `invoice.audited`, `alert.triggered`, `report.generated`.
- [ ] Send webhooks with `X-Delivery-ID` (UUID) and `X-Signature` (HMAC-SHA256) headers.
- [ ] Log all delivery attempts: status_code, latency_ms, retry_count, response_body_preview.
- [ ] Include pre-built connector templates for MISA, Fast Accounting, generic ERP.
- [ ] Write tests verifying subscription CRUD, event dispatch, and signature verification.

## Design Notes

- **Dispatcher**: Async webhook sender reusing patterns from v9 US-123 webhook hub.
- **Templates**: JSON config files in `data/schemas/connectors/`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v13_webhook_registry.py` — CRUD, dispatch, HMAC |
| Integration | Create subscription → trigger event → verify delivery log entry |
