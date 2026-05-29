# Exec Plan: US-025 Database Persistence and SQLite Migration

## Goal

Replace the local flat file JSON database (`invoices_db.json`) with a robust SQLite database managed via Flask-SQLAlchemy. This ensures data consistency, supports concurrent writes from asynchronous download workers, and establishes a relational schema for invoices, line items, and partner metadata.

## Scope

In scope:
- Add `Flask-SQLAlchemy` and `Flask-Migrate` dependencies.
- Implement database models in `invoices/models.py` (Invoice, LineItem, Partner, SystemConfig, SchedulerLog).
- Migrate data loading/saving service layers (`invoices/service.py`, `invoices/scheduler.py`, `invoices/mst_service.py`) to ORM query interactions.
- Enable SQLite Write-Ahead Logging (WAL) mode for handling concurrent read/write transactions.
- Implement a startup migration wrapper that automatically backs up `invoices_db.json` to `invoices_db.json.bak` and imports all legacy JSON records into the SQLite tables on the first launch.

Out of scope:
- Multi-tenant database partitioning.
- Changing frontend template layouts or API endpoints shapes.

## Risk Classification

Risk flags:
- Data model: Changing the entire storage layer, schema mapping, and persistence layer.
- Existing behavior: Affects authentication, history logging, and invoice retrieval services.

Hard gates:
- Data loss or migration: Moving legacy records from flat-file JSON format to relational tables.

## Work Phases

1. **Discovery**: Mapping the exact shapes of invoices, settings, and logs currently stored in JSON to SQLite relationships.
2. **Design**: Creating model definitions with proper constraints, foreign keys (cascade on delete), and transaction retry wrappers.
3. **Validation planning**: Designing tests for cascading deletes, concurrent writing stress, and data migration.
4. **Implementation**: Writing models, routes, database migrations, updates to service layer, and startup execution hooks.
5. **Verification**: Executing pytest suite and validating performance under concurrency.
6. **Harness update**: Documenting proof, updating the backlog and the test matrix.

## Stop Conditions

Pause for human confirmation if:
- Legacy JSON files contain corrupt or unrecognized structures that make the automatic migration fail.
- Database transaction errors occur under lock conditions during parallel downloads.
