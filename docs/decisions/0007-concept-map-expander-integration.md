# ADR-0007: Interactive Concept Map Expander Integration

## Context
We need to enrich the Compliance Concept Map Explorer of the GDT Invoice Hub by adding a dynamic Concept Map Expander viewer. This allows taxpayers and auditors to expand any tax compliance node (v24 to v70) into a structured 7-page field guide adhering to the `concept-map-expander` relational grammar, containing:
1. Orientation
2. Core Model
3. Scope Rings
4. Relation Grammar
5. Mechanism & Dynamics
6. Boundaries & Failure Cases
7. Application & Learning Path

This guide must render interactively in the web frontend, retrieve real-time alerts and logs from database queries to show empirical failure case stats, and be fully searchable and navigable.

## Decision
1. **API Development**: Expose a new REST API endpoint `/api/compliance/concept-map/expand/<version_id>` in `invoices/routes/core.py`. This endpoint will return a structured JSON representing the 7-page map details.
2. **Database Queries**: Query actual warning/audit databases dynamically for the selected compliance node to return the number of warnings/logs as live evidence.
3. **UI Integration**: In `templates/compliance_concept_map.html`, add a modern tab-based reader in the sidebar or a dedicated bottom panel with glassmorphism, transition animations, search filtering, and next/prev page navigation.
4. **Test Suite**: Expand tests in `tests/test_compliance_concept_map.py` to cover the new endpoint.

## Consequences
- Enhanced compliance diagnosis for users.
- Live telemetry stats shown directly in the concept map UI.
- Fully verified via standard automated tests.
