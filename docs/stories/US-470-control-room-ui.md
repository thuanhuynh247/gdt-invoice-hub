# Spec: US-470 — Interactive Systems-Level Tax Audit Control Room UI

## Status
planned

## Lane
normal

## Product Contract

The system provides a **Unified Tax Audit Control Room** dashboard that aggregates all tax risk areas and compliance issues (VAT anomalies, late signing, cash payments, blacklisted partners, transfer pricing markups) into a single interactive glassmorphic interface, complete with a System Tax Health Score and interactive risk trees.

## Acceptance Criteria

- [ ] Web view `/v35-compliance` exposes the Control Room UI with dark/light mode glassmorphic styling.
- [ ] Displays **System Tax Health Score** (0-100) calculated by penalizing critical/major/minor issues from the database.
- [ ] Implements an **Interactive Risk Tree** in SVG/CSS allowing the user to click nodes to expand/collapse and see specific violating invoices.
- [ ] Fully integrates data from models and compliance services dynamically.
