# US-142 Resilient Sync Queue Manager

## Status

planned

## Lane

normal

## Product Contract

The application must support asynchronous background synchronization of VAT invoices for multiple taxpayer profiles concurrently. Failures (such as connection timeouts or invalid passwords) on one taxpayer profile must be isolated and must not block or crash background crawls for other registered taxpayer profiles.

## Relevant Product Docs

- `docs/product/v11_roadmap.md`

## Acceptance Criteria

- [ ] Create a `ResilientSyncQueue` using a background `ThreadPoolExecutor` to handle parallel crawl jobs.
- [ ] Implement isolated exception handling to ensure that failing profiles are logged and marked but do not interfere with other tenants' sync execution.
- [ ] Implement scheduling options to configure synchronization times or periodic cron-like triggers.
- [ ] Write integration tests simulating multiple taxpayer sync operations, asserting isolated failures.

## Design Notes

- **Module**: `invoices/scheduler.py` or new queue manager.
- **Concurrent workers**: Thread-safe pool wrapping GDT crawler logic.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit / Integration | `pytest tests/test_v11_sync_resiliency.py` simulating parallel sync and isolated failures |
