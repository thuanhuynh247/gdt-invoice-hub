# US-013 Supabase Design System Upgrade & No-Emoji Compliance

## Status

completed

## Lane

normal

## Product Contract

The application should present a premium, cohesive Postgres-emerald/Supabase dark aesthetic. The UI should load cleanly, prevent styling flicker, replace all emojis with vector SVG icons, support show/hide toggles for password input fields, and ensure minimum 44px touch targets on mobile screen viewports.

## Relevant Product Docs

- `01_constitution.md` (Principle 1: Simple > Fancy, Principle 7: Style Selection)
- `02_specification.md` (Vietnamese UI/UX layout)
- `open-design/design-systems/supabase/DESIGN.md`

## Acceptance Criteria

- [x] All UI emoji characters (⚡, 📂, 🏢, 📋, 📊, 📥, 🗑️, 📄, 🖨️, etc.) are replaced with appropriate vector SVG/Bootstrap Icons.
- [x] Bootstrap Icons stylesheet is linked from CDN in `templates/base.html`.
- [x] Dark theme colors match Supabase's dark palette (near-black page background `#171717`, cards `#1c1c1c`, emerald green accent `#3ecf8e`).
- [x] The theme toggle prevents screen flashes/flicker and functions smoothly.
- [x] The login page headings are written in correct Vietnamese with proper accents.
- [x] Password input on the login page contains a visibility toggle button (with eye/eye-slash icons) that switches the input type dynamically.
- [x] Touch targets are at least 44px vertically, including form controls, search switches, and buttons.
- [x] Visual transitions on hover, focus, and state changes are smooth (150ms-250ms).
- [x] Pytest suite remains passing with no regressions.

## Design Notes

- **UI Surfaces**: `templates/base.html`, `templates/login.html`, `templates/invoices.html`, `static/css/style.css`, `static/js/main.js`
- **Asset CDNs**: Bootstrap Icons `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css`

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest` validation suite passes |
| Integration | All route controllers serve clean, valid HTML markup |
| E2E | Browser automation loads and verifies visual/behavioral UI updates |

## Harness Delta

N/A

## Evidence

- Running unit and integration tests: 38 passed successfully.
- Applied styling upgrades to static/css/style.css, templates/base.html, templates/login.html, and templates/invoice_pdf.html.
