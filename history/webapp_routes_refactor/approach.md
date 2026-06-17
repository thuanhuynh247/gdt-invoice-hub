# Approach: Webapp Routes Refactoring

## Recommended Approach

We will decompose `invoices/routes.py` into a package folder `invoices/routes/` containing:
- `__init__.py`: Defines the single `invoices_blueprint`, imports all routing sub-modules to register their endpoints on the blueprint, and exposes backward-compatible symbols (`invoices_blueprint`, `DOWNLOAD_TASKS`, `render_html_to_pdf`).
- `core.py`: Core invoice list, detail, export, download, and stats APIs.
- `reconciliation.py`: Bank transaction and reconciliation APIs.
- `ocr.py`: OCR Vision processing APIs.
- `compliance.py`: Versioned tax compliance API endpoints (v24-v70).
- `mitigation.py`: AI-driven audits, correction proposals, and mitigation letters.
- `settings.py`: settings, blacklist, logs, and testing APIs.

We will also create a new module `invoices/workers.py` to house the background worker initialization logic, and import it in `app.py` to keep it clean.

### Rejected Alternatives
- *Rejected Alternative 1: Multiple Flask blueprints.* This was rejected because it would require modifying all frontend templates and test suites, violating the constraint of 100% backward compatibility (Decision D4).
- *Rejected Alternative 2: Leaving versioned compliance routes in routes.py and only splitting core routes.* This was rejected because it does not solve the tech debt of the 13k line monolith effectively; the compliance routes alone make up over 10,000 lines of code.

## Risk Map

| Component | Risk Level | Reason | Proof Needed |
|---|---|---|---|
| Circular Imports | MEDIUM | Modules under `invoices/routes/` might need reference sharing or import from `invoices.routes` itself. | Verify that Python is able to import all modules without circular errors. |
| Test suite execution | HIGH | Refactoring the monolith could accidentally omit imports or handlers, causing tests to fail. | Run the entire test suite (`pytest`) and ensure all tests pass. |
| Background Workers | LOW | Moving worker start threads might alter startup sequence or environment checks. | Verify webapp starts successfully without error logs. |

## File & Order Boundaries

1. Create `invoices/workers.py` and move worker startup logic there. Modify `app.py` to use it.
2. Verify existing test suite runs successfully as the baseline.
3. Create package `invoices/routes/` and its sub-modules (`core.py`, etc.).
4. Move route definitions from `invoices/routes.py` into respective files.
5. In `invoices/routes/__init__.py`, import all sub-modules to attach routes to `invoices_blueprint`, and export the required symbols.
6. Delete the old `invoices/routes.py`.
7. Run the test suite to verify correctness.

## Relevant Learnings
- **[20260602] Smart SQLite CP1258 Decoding Factory & Mock Test Isolation:** Ensure mock tests run smoothly without requiring database setup.
- **Circular Imports Avoidance:** Do local imports inside endpoints or service layers if any service depends on symbols defined in `routes` (e.g. `render_html_to_pdf` in `service.py`).
