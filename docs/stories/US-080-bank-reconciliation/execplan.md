# Exec Plan: US-080 & US-081 AI-Powered Multi-Source Bank Reconciliation

## Goal
Implement a secure SQLite database schema, a multi-source statement ingestion parser (Excel/CSV), and a Soundex phonetic matching algorithm that automatically reconciles banking transfers with purchase and sales XML invoices with >= 90% accuracy.

## Scope

### In scope:
- Database table migrations (`bank_transactions` table added dynamically).
- File statement parsers supporting Vietcombank and Techcombank transaction sheets.
- Advanced Vietnamese string canonicalization and abbreviation cleaning modules.
- REST API endpoints for uploading, listing, auto-matching, and manual matching overrides.
- Zero-dependency unit and integration tests.

### Out of scope:
- Live web scrapers accessing the commercial bank login portal.
- Automated wire transfers or payout executions.

---

## Risk Classification

Risk flags:
- **Data Model**: Adds new tables, requires foreign key constraints.
- **External Systems**: Handles third-party statement uploads (Excel/CSV parsed via openpyxl).
- **Public Contracts**: Exposes new reconciliation REST endpoints.

Hard gates:
- None (No user data loss or migration threat; new table additions only).

---

## Work Phases

### Phase 1: Database Foundation & Schema Setup
- Expand `invoices/models.py` with `BankTransaction` schema.
- Implement live database migrations matching SQLite configurations.

### Phase 2: Ingester & Parser Module
- Develop standard mapping configurations for Vietcombank and Techcombank.
- Implement a parser service that processes uploaded statements using `openpyxl` and returns structured JSON datasets.

### Phase 3: Phonetic & String Matching Engine
- Write Vietnamese diacritic removal and text normalization helpers.
- Implement the Soundex & Levenshtein matching engine.
- Write strict amount constraints check logic.

### Phase 4: REST API Endpoints
- Implement routes `/api/bank/reconcile/upload` and `/api/bank/reconcile/auto` in `invoices/routes.py`.

### Phase 5: Verification & Harness Logs
- Write a specialized test suite `tests/test_bank_reconcile.py`.
- Execute verification steps and log traces into `harness.db`.

---

## Stop Conditions
Pause and ask for human input if:
- Upload formats contain columns with encrypted metadata.
- Excel layouts contain non-standard multiple sheets or merged cells that interfere with openpyxl parsing.
