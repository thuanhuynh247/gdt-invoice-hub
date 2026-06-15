# Discovery: Webapp Routes Refactoring

## Architecture Snapshot

- **Entry Point:**
  - `app.py`: Flask application factory (`create_app()`) starts background daemons and registers the `invoices` blueprint.
  - `invoices/__init__.py`: Exports the `invoices_blueprint`.
- **Core Controller:**
  - `invoices/routes.py`: A massive monolith (13,602 lines) containing all routing endpoints (core, settings, reconciliation, OCR, version compliance `/v24` to `/v70`, etc.).
- **Background Workers:**
  - Prefetch worker, scheduler worker, PDF ingestion worker, and sync daemon are started inside `create_app()` in `app.py`.

## Constraints

- **Framework version:** Python 3.x with Flask and SQLite database.
- **Dependencies:** `xhtml2pdf`, `reportlab`, `pytest`.
- **Quality Gates:** All existing 146 unit test suites containing 200+ test assertions must pass. Any breaking endpoint changes will fail the test suite immediately.
- **Import references:**
  - `invoices/service.py` imports `render_html_to_pdf` from `invoices.routes`.
  - `tests/test_async_download.py` imports `DOWNLOAD_TASKS` from `invoices.routes`.
  - Numerous test suites import `invoices_blueprint` from `invoices.routes`.

## Summary

- **Exists:** A working Flask application with solid but monolith-bound route logic.
- **Missing:** Code modularity. Adding or editing any endpoint is difficult due to the file size of `routes.py`.
- **Warnings:** Potential circular dependency risks when splitting routes that reference each other or services. We must ensure `invoices/routes/__init__.py` exposes all expected properties (`invoices_blueprint`, `DOWNLOAD_TASKS`, `render_html_to_pdf`) to preserve imports.
