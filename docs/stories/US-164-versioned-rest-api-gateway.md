# US-164 Versioned REST API Gateway

## Status

planned

## Lane

high_risk

## Product Contract

The application must expose a versioned public REST API (`/api/v1/`) enabling external ERP systems and accounting software to programmatically query invoices, trigger audits, and retrieve reports. Authentication uses API keys with per-key rate limiting.

## Relevant Product Docs

- `docs/product/v13_roadmap.md`

## Acceptance Criteria

- [ ] Implement Flask Blueprint for `/api/v1/` with versioned resource endpoints.
- [ ] Create `APIKey` model with fields: key_hash, name, owner, rate_limit, created_at, is_active.
- [ ] Implement API key authentication middleware checking `X-API-Key` header.
- [ ] Enforce rate limiting (default: 100 requests/minute per key) with 429 responses.
- [ ] Expose endpoints: `GET /api/v1/invoices`, `GET /api/v1/audits`, `GET /api/v1/reports`.
- [ ] Auto-generate OpenAPI 3.0 spec accessible at `GET /api/v1/docs`.
- [ ] Use standard JSON envelope: `{"status": "ok", "data": [...], "pagination": {...}}`.
- [ ] Write comprehensive tests for auth, rate limiting, and data retrieval.

## Design Notes

- **Module**: New `invoices/api_gateway.py` with Blueprint.
- **Rate limiter**: In-memory counter with sliding window per (IP + API key).
- **OpenAPI**: Manual or flask-apispec/flasgger generated.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v13_api_gateway.py` — auth, rate limit, response format |
| Integration | External HTTP client can query invoices with valid API key |
