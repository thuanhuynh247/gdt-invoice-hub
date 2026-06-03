# Current Story Pack: US-191 - Database Schema & Catalog Management

## Context & Alignment
- **Epic**: Epic 1: Decree 132 Related-Party & EBITDA Cap
- **Story ID**: `US-191`
- **Objective**: Extend database model for `Partner` to include Decree 132 relationship code column (`decree_132_relationship`), perform migrations/initializations, and expose CRUD api endpoints for relationship assignment in `routes.py`.

---

## 🚪 Entry State
- The `Partner` model in `invoices/models.py` does not contain the `decree_132_relationship` attribute.
- The SQLite tables (both primary and multi-tenant databases) lack the `decree_132_relationship` column.
- There are no HTTP endpoints in `invoices/routes.py` to retrieve or configure related-party codes for suppliers.

---

## 🏁 Exit State
1. **Database Schema Extension**:
   - `Partner` model in `invoices/models.py` has a new column `decree_132_relationship = db.Column(db.String(10), nullable=True)`.
   - `Partner.to_dict()` includes the `"decree_132_relationship"` key.
2. **Automatic Migrations**:
   - `app.py` dynamically checks `PRAGMA table_info(partner);` on startup and runs `ALTER TABLE partner ADD COLUMN decree_132_relationship VARCHAR(10) NULL;` if the column is missing.
3. **API Endpoints**:
   - `GET /api/partners` returns the list of partners.
   - `POST /api/partners/<mst>/decree-132` updates the relationship code for a specific partner. Validates that the input code is either empty/null or one of the valid letters A through L (Decree 132/2020/NĐ-CP clauses).
4. **Validation Tests**:
   - A new test suite `tests/test_v19_us191_partner_schema.py` is written to verify:
     - The column exists on the `Partner` model and database.
     - The API endpoints successfully fetch and update the `decree_132_relationship` with proper validation.

---

## 📂 Files Likely Touched
- `invoices/models.py`
- `invoices/routes.py`
- `app.py`
- `tests/test_v19_us191_partner_schema.py` (New test file)

---

## 🔍 Feasibility Assumptions & Risk Mitigations
- **Assumption 1**: SQLite permits adding nullable columns dynamically without needing database rebuilds.
  - *Mitigation*: Handled via dynamic `ALTER TABLE ... ADD COLUMN ...` in the `app.py` startup migration checks block.
- **Assumption 2**: Multi-tenant database connections (`tenant_<mst>.db`) initialized via `TenantRoutingSession` will also receive schema updates dynamically when they are loaded or during tests.
  - *Mitigation*: Ensure standard db init and migration logic is robust and runs inside the app context.

---

## 🧪 Verification Plan
- **Preflight & Compilation**:
  - Run compile check to verify syntax: `venv\Scripts\python.exe -m compileall app.py invoices\models.py invoices\routes.py`
- **Tests Execution**:
  - Run new unit tests: `python scripts/harness_win.py validate --cmd "venv\Scripts\python.exe -m pytest tests/test_v19_us191_partner_schema.py -v"`
- **Full Suite Check**:
  - Validate the entire codebase: `python scripts/harness_win.py validate --cmd "scripts\validate.bat"`

---

## 🛑 Out of Scope
- EBITDA calculations and net interest expense deduction caps (handled under `US-192`).
- Compilation of Form 01/132-NĐ-CP related-party disclosure sheets (handled under `US-192`).
- UI screens / front-end visual elements for managing related-party relationship codes.

---

## 🧩 Bead Mapping
*(To be created and registered using `br` after validation accepts feasibility)*
- **Bead US-191-1**: Extend `Partner` database model and add live migrations check.
- **Bead US-191-2**: Implement partner query and related-party code update APIs in `invoices/routes.py`.
- **Bead US-191-3**: Add unit and integration tests under `tests/test_v19_us191_partner_schema.py`.
