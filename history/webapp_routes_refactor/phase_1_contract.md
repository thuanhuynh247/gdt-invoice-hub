# Phase Contract: Phase 1 - Verification & Modular Setup

**Entry state:**
- The Flask application boots correctly with background threads (`start_captcha_prefetch_worker`, `start_scheduler_worker`, `start_dynamic_pdf_ingestion_thread`, and `GDTSyncDaemon`) started inline inside the `create_app()` factory in `app.py`.
- `invoices/routes.py` is a 13,602-line monolithic file containing all HTTP endpoints.
- Baseline test suite (`pytest`) runs successfully.

**Exit state:**
- Background worker initialization logic is refactored out of `app.py` and consolidated within a clean module `invoices/workers.py`.
- `app.py` is updated to call `invoices/workers.py` for worker initialization.
- A skeleton folder `invoices/routes/` is created.
- The system boots normally, background workers launch without error logs, and all tests pass successfully.

**Demo:**
- Verify application launches successfully and logs confirm daemon threads are active.
- Run `pytest tests/test_scheduler.py` and ensure they pass.

## Stories

| Story | What Happens | Unlocks | Done |
|---|---|---|---|
| US-1.1 | Establish and verify baseline test suite run. | Confirms codebase safety. | [x] |
| US-1.2 | Refactor background worker threads out of `app.py` into `invoices/workers.py`. | Cleaner `app.py` structure. | [x] |
| US-1.3 | Scaffold modular directory structure `invoices/routes/` and verify imports. | Prepared layout for Phase 2. | [x] |

## Out/Success/Pivot
- **Success Criteria:** Pytest runs successfully and workers module isolates background threads cleanly.
- **Pivot Trigger:** If moving workers causes threading synchronization issues or delays application setup, pivot to keeping worker imports but starting them via a hook.
