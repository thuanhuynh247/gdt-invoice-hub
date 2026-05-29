# Validation: US-025 Database Persistence and SQLite Migration

## Proof Strategy

All database schemas, relationship cascades, dynamic data aggregation, and migration helpers must be fully tested using `pytest`. The application must start up, perform the migration from `invoices_db.json` to SQLite, and execute all existing unit, integration, and E2E browser tests without failure.

## Test Plan

| Layer | Cases |
| --- | --- |
| **Unit** | - Test relationship cascades (deleting an Invoice deletes all related LineItems).<br>- Test SystemConfig storage and password encryption helper logic.<br>- Test Partner directory persistence and MST caching updates. |
| **Integration**| - Test data migration module: Load mock legacy `invoices_db.json`, execute migration script, and verify SQLite tables have matching structures.<br>- Test transaction locking under concurrency: Spin up concurrent database writer threads mimicking parallel downloaders and verify zero locks or crashes. |
| **E2E** | - Execute the Selenium web test suite `tests/test_e2e_ui.py` to confirm that login, search, stats rendering, modal drawer viewing, and theme switching behave identically. |

## Fixtures

A temporary database directory containing:
- Legacy `invoices_db.json` files representing parsed invoices and partner registries.
- Invalid or missing JSON databases to test fallback setup.

## Commands

```bash
# Run database and model test suites
venv\Scripts\pytest -v tests/test_db_persistence.py

# Run full project validation
scripts\validate.bat
```
