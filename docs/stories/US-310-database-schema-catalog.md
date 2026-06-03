# Story Specification: US-310 — Database Schema & Catalog Management

## 📋 Context & Business Value
Under Decree 132/2020/NĐ-CP, transactions between related parties are subject to specific disclosure and transfer pricing regulations. To track and flag related-party suppliers, the system catalog must support assigning standard relationship codes (letters A through L) to partners.

---

## 🎯 Acceptance Criteria

### 1. Database Schema Extension
- Extend the `Partner` model in `invoices/models.py` with a new column `decree_132_relationship` (nullable, up to 10 characters).
- Include `decree_132_relationship` in `Partner.to_dict()` outputs.

### 2. Auto-Migration on App Startup
- Dynamically check the SQLite database schema on application start.
- If the column `decree_132_relationship` is missing from the `partner` table, execute an `ALTER TABLE partner ADD COLUMN decree_132_relationship VARCHAR(10) NULL;` migration automatically.

### 3. API Endpoints
- **GET `/api/partners`**: Authenticated query to fetch partner profiles, including their Decree 132 relationship code.
- **POST `/api/partners/<mst>/decree-132`**: Updates the related-party code.
  - Returns `401` for anonymous users.
  - Returns `403` for viewers (requires editor or admin role).
  - Validates that the code is either null/empty or belongs to the range `A` to `L` (case-insensitive, normalized to uppercase).
  - Returns `400` on invalid inputs.

---

## 🛠️ Verification & Test Plan
- Run Pytest verification using `tests/test_v19_us191_partner_schema.py`.
- Verify relationship code persistence, role-based checks, and input validation.
