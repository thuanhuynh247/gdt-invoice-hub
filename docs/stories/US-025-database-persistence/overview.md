# Overview: US-025 Database Persistence and SQLite Migration

## Current Behavior

All persistent records (invoices, unique partner directory listings, scheduler job frequencies, and historical execution logs) are stored within a single flat file database at `data/invoices_db.json`. Any read or write operation requires loading and parsing the entire file into memory, editing the dictionaries, and writing the entire serialized payload back to disk. This causes performance overhead and presents concurrency hazards when async batch downloaders attempt simultaneous writes.

## Target Behavior

A relational SQLite database at `data/invoices.db` manages data storage. An ORM layer (Flask-SQLAlchemy) handles structured queries, inserts, edits, and deletions. SQLite is configured to use Write-Ahead Logging (WAL) mode to permit concurrent read and write operations. On the initial startup of the updated application, any existing `invoices_db.json` database is backed up to `invoices_db.json.bak` and its records are migrated to the SQLite database.

## Affected Users

- **Accountants / System Operators**: Benefit from faster search queries and reliable background report generation.
- **Developers**: Interact with a structured relational model instead of complex dictionary manipulation.

## Affected Product Docs

- `docs/ARCHITECTURE.md` (Update references to state and database design).

## Non-Goals

- Migrating to client-server RDBMS (e.g. Postgres, MySQL) at this phase.
- Modifying UI styles or client-visible route payloads.
