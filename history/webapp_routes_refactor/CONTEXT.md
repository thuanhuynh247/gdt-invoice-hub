# Webapp Routes Refactoring - Context

**Feature slug:** webapp_routes_refactor
**Date:** 2026-06-15
**Exploring session:** complete
**Scope:** Deep
**Domain types:** ORGANIZE | CALL | SEE

## Feature Boundary

This feature refactors the monolithic `invoices/routes.py` (which spans over 13,000 lines of code) into a modular structure under `invoices/routes/` grouped by business domain, and cleans up the background daemon thread instantiation in `app.py` into a separate management module without breaking any existing HTTP routing contracts, template lookups, or automated tests.

## Locked Decisions

These are fixed. Planning must implement them exactly.

- **D1:** Split `invoices/routes.py` into individual files by business domain:
  - `invoices/routes/core.py`: Search, download, excel exports, stats, and detail retrieval APIs.
  - `invoices/routes/reconciliation.py`: Bank statement reconciliation and transaction matching APIs.
  - `invoices/routes/ocr.py`: Vision OCR uploading and paper invoice digitizing APIs.
  - `invoices/routes/compliance.py`: Versioned compliance endpoints (`/v24` through `/v70`).
  - `invoices/routes/mitigation.py`: AI audit, correction proposals, and mitigation letters.
  - `invoices/routes/settings.py`: App settings, blacklist, logs, and email testing endpoints.
- **D2:** Absolute backward compatibility must be maintained. All HTTP paths, methods, parameters, and python endpoint function names must be kept exactly identical to prevent breaking any frontend scripts, template routes, or testing suites.
- **D3:** Move background worker thread startup logic out of `create_app()` in `app.py` and into `invoices/workers.py`.
- **D4:** Retain a single `invoices_blueprint` definition in `invoices/__init__.py` and mount all split route handlers to it so that `url_for('invoices.<endpoint>')` remains valid without modification.

### Agent's Discretion

- The agent has the discretion to organize the internal module imports in `invoices/__init__.py` or `invoices/routes/__init__.py` as long as it correctly mounts the routes onto the single `invoices_blueprint`.
- The agent has discretion on how to parameterize and import dependencies within each sub-route file to prevent circular import loops.

## Existing Code Context

### Reusable Assets

- `invoices/routes.py` - The monolithic source of all routes. Will be split up and deleted once verified.
- `app.py` - Contains the Flask `create_app()` factory and background worker startup logic.

### Established Patterns

- **Blueprint Mounting:** Flask blueprints are defined once and endpoints are attached using decorator syntax (e.g. `@invoices_blueprint.get("/...")`).
- **Worker Initialization:** Workers are conditionalized with `if not app.config.get("TESTING") and os.getenv("TESTING") != "True":` checks.

### Integration Points

- `invoices/__init__.py` - This is where the `invoices_blueprint` is defined and where the split modules should be imported to attach their routes.
- `app.py` - Needs to import and call `invoices_blueprint`, and delegate worker startup to the new worker management module.

## Canonical References

- [invoices/routes.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes.py) - Current monolithic file.
- [app.py](file:///d:/LearnAnyThing/Webapp%20XML/app.py) - Application factory and startup.

## Outstanding Questions

### Deferred To Planning

- [x] Circular Imports - How to prevent circular imports when splitting the routes since they reference services and models which might reference other modules?
- [x] Test Coverage verification - How to run pytest to verify 100% of the routes remain fully functional?

## Deferred Ideas

- None.

## Handoff Note

CONTEXT.md is the source of truth. Decision IDs are stable. Planning reads locked decisions, code context, canonical references, and deferred-to-planning questions. Validating and reviewing use locked decisions for coverage and UAT.
