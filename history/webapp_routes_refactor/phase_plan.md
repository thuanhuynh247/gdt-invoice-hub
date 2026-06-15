# Phase Plan: Webapp Routes Refactoring

Mode: `standard_feature`

## Feature Summary

This feature refactors the monolithic `invoices/routes.py` (which contains over 13,000 lines of code) by decomposing it into modular files grouped by business domain. It also cleans up the Flask app factory (`app.py`) by moving background worker initialization into a separate management module. It guarantees 100% backward compatibility with existing routes, tests, and template engines.

## Phase Overview

| Phase | What Changes | Why Now | Demo | Unlocks |
|---|---|---|---|---|
| **Phase 1: Verification & Modular Setup** | Baseline test run, create `invoices/workers.py` to move background threads out of `app.py`, set up skeleton package structure under `invoices/routes/`. | Establishes a clean baseline and verifies the worker refactoring before touching the massive routes file. | Pytest baseline passes, worker startup functions normally on app launch. | Clean and tested foundation for the routes decomposition. |
| **Phase 2: Decomposition & Switchover** | Migrate all endpoints from `invoices/routes.py` into their respective sub-modules, dynamically attach them to the single `invoices_blueprint`, delete `invoices/routes.py`, and expose compatible imports. | Deconstructs the large monolith and verifies that the new modular routing architecture is fully compatible with tests and templates. | Complete pytest execution passes, all endpoints respond correctly. | Elimination of the monolith tech debt, making feature expansion modular and token-efficient. |

## Order Check
- Phase 1 isolates the background workers and sets up the modular folder structure. This ensures we don't mix app factory refactoring with routes splitting.
- Phase 2 performs the heavy route decomposition and switchover once the layout is ready.
- Both phases verify outcomes with pytest.

## Approval Summary

- **Current Phase:** Phase 1 (Verification & Modular Setup).
- **Picture after it:** Background workers are isolated in `invoices/workers.py`. The app starts normally. Empty skeletons are created under `invoices/routes/` with tests passing.
- **Deferred work:** Phase 2 (full route decomposition and old `routes.py` deletion).
