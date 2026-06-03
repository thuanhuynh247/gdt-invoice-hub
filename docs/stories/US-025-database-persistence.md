# US-025: Database Persistence and SQLite Migration

## Status

implemented

## Lane

high-risk

## Product Contract

The application must replace the local flat file JSON database (`invoices_db.json`) with an SQLite database managed via Flask-SQLAlchemy. This ensures data consistency, supports concurrent writes from async download tasks, and provides a proper relational schema for invoices, line items, and partner metadata.

## High-Risk Story Folder

This is classified as a High-Risk story because it touches data migration and schemas. The detailed story specifications are located in:
- [Execution Plan (execplan.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-025-database-persistence/execplan.md)
- [Overview (overview.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-025-database-persistence/overview.md)
- [Design (design.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-025-database-persistence/design.md)
- [Validation (validation.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-025-database-persistence/validation.md)

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)
- [docs/ARCHITECTURE.md](file:///d:/LearnAnyThing/Webapp%20XML/docs/ARCHITECTURE.md)

## Acceptance Criteria

- [x] Add `Flask-SQLAlchemy` and `Flask-Migrate` to `requirements.txt`.
- [x] Implement database models in `invoices/models.py` (Invoice, LineItem, Partner, SystemConfig, SchedulerLog).
- [x] Migrate the current data loading/saving logic in `invoices/service.py` to use SQLAlchemy ORM queries instead of loading the entire JSON file.
- [x] Implement an automatic database initialization / migration script during startup.
- [x] Ensure that during concurrent writes (like batch-downloading and importing XML files simultaneously), transactions are handled properly with retry loops to avoid database lock exceptions.
- [x] Back up existing JSON database to `invoices_db.json.bak` during first startup and perform a one-time migration of existing data to the SQLite database.

## Design Notes

- **Database Engine**: SQLite.
- **ORM**: Flask-SQLAlchemy (SQLAlchemy 2.0 style queries).
- **Concurrent Writes**: Use transaction context managers and configure sqlite journal mode to WAL (`journal_mode=WAL`) for better concurrency.
- **UI Surfaces**: No visible UI changes, but backend queries must execute faster and more reliably.

## Validation

See details in [Validation Specifications](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-025-database-persistence/validation.md).

## Evidence

None.
