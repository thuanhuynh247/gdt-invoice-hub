# US-143 CAPTCHA Solver Analytics Dashboard

## Status

planned

## Lane

normal

## Product Contract

The application must capture real-time performance metrics of the local CAPTCHA solving engine (success count, fail count, average latency) and expose them via a dedicated UI panel and API endpoint. This enables users and admins to detect portal changes or OCR degradation.

## Relevant Product Docs

- `docs/product/v11_roadmap.md`

## Acceptance Criteria

- [ ] Track solve status (success/fail) and time taken inside the CAPTCHA solver execution.
- [ ] Implement endpoint `GET /api/sync/health` returning solver statistics and overall crawler status.
- [ ] Render a premium Glassmorphism monitoring card displaying real-time CAPTCHA stats, solve rates, and latency.
- [ ] Write tests verifying statistics accumulation and correct JSON endpoint response.

## Design Notes

- **Metrics Store**: Thread-safe in-memory or SQLite stats counter.
- **Route**: `/api/sync/health` returning accumulated stats.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Verify stats recording and accuracy calculations |
| Integration | Verify API `/api/sync/health` returns correct JSON payload |
