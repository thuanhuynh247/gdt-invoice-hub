---
name: webapp-compliance-hub
description: Build, modernize, and verify V-Series Compliance Hubs (V50-V80+) in Webapp XML. Use when creating new compliance screens, refactoring existing hub templates, standardizing Jinja2 Lego components, or writing pytest verification suites for tax compliance modules.
---

# Webapp Compliance Hub Specialist

Build, standardize, and verify modular Compliance Hubs (e.g. V55-V79+) within the Webapp XML platform. Every hub serves as an interactive regulatory audit interface adhering to the Wise Fintech design system and backed by automated tests.

## Hub Architecture Patterns

Every Compliance Hub consists of three tightly coupled layers:

1. **Route & Data Aggregation** (`invoices/routes/compliance.py` or `invoices/routes/compliance_pages_data.py`):
   - Endpoint: `@invoices_blueprint.route('/compliance/v<number>')`
   - Fetch taxpayer context from active session (`get_current_mst()`).
   - Query tenant SQLite database via `invoices.service`.
   - Return structured metrics, anomaly rows, and filter parameters to the template.

2. **Jinja2 Lego Template** (`templates/v<number>_compliance_hub.html`):
   - Inherits from base layout or includes Lego components.
   - Implements 4 standard UI zones:
     - **Header Bar**: Hub title, regulation badge (e.g., `Luật 149/2024`, `Decree 123`), status indicator.
     - **Metric Bento Grid**: 3-4 KPI stat cards (`Total Audited`, `Anomaly Count`, `At-Risk Amount`, `T-Score Impact`).
     - **Interactive Filter Toolbar**: Date range, risk level dropdown, text search, and export actions.
     - **Data Table / Anomaly Ledger**: Glassmorphic table with sticky header, monospace numbers (`Roboto Mono`), and status pills (`--badge-success`, `--badge-warning`, `--badge-danger`).

3. **Automated Verification Suite** (`tests/test_v<number>_compliance.py` or `tests/test_e2e_ui.py`):
   - Render check: HTTP 200 and presence of core HTML IDs.
   - Calculation check: Precision verification of tax calculations and risk penalties.
   - Filter check: Query parameters filter data without 500 errors.

---

## Step-by-Step Implementation Workflow

### Step 1: Define Regulatory Contract & Data Schema
- Identify the governing legal basis (e.g., Circular 78, Decree 123, Law 149, IFRS, Pillar 2).
- Define input parameters, risk thresholds, and anomaly conditions.
- If creating a new hub number, register it in `docs/CONCEPT_MAP.md` and `docs/stories/`.

### Step 2: Implement Backend Route & Analytics
- Open `invoices/routes/compliance.py`.
- Add or update the dedicated route handler.
- Ensure all DB access uses the tenant-isolated connection manager (`invoices.service.get_tenant_db()`).
- Wrap queries in try-except blocks, returning graceful fallback states if the dataset is empty.

### Step 3: Craft the Wise Fintech Template
- Create or refine `templates/v<number>_compliance_hub.html`.
- Use HSL design tokens from `static/css/`:
  - Backgrounds: `background: hsla(220, 20%, 10%, 0.7); backdrop-filter: blur(12px);`
  - Borders: `border: 1px solid hsla(220, 20%, 30%, 0.3);`
  - Badges: `.badge-success`, `.badge-warning`, `.badge-danger`
  - Monetary values: `<span class="font-mono">{{ "{:,.0f}".format(amount) }} VND</span>`
- Ensure every interactive button and table has unique, semantic `id` and `data-testid` attributes.

### Step 4: Verify with Pytest
- Execute targeted test suite:
  ```bash
  pytest tests/test_e2e_ui.py -k "v<number>" -v
  ```
- If tests fail, diagnose using traceback, apply single-source fixes, and re-test until green.

### Step 5: Sync Harness Telemetry
- Record task completion and test outcome:
  ```bash
  python scripts/harness_win.py trace --summary "Implemented V<number> Compliance Hub" --outcome success --story US-V<number>
  ```

---

## Completion Checklist

- [ ] Route registered in `invoices/routes/compliance.py` with multi-tenant safety.
- [ ] Template follows Wise Fintech glassmorphic design and HSL tokens.
- [ ] Monetary amounts formatted with monospace font.
- [ ] Responsive layout verified for mobile/desktop.
- [ ] Pytest verification passes with 0 failures.
- [ ] Telemetry logged to `harness.db`.
