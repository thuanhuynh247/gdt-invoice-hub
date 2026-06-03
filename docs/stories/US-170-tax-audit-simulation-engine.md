# US-170 Tax Audit Simulation Engine

## Status

implemented

## Lane

normal

## Product Contract

The application must run a comprehensive simulated audit suite mimicking GDT inspector checklists to assess overall tax compliance and assign a consolidated Tax Audit Risk Score (T-Score) with visual risk flags.

## Relevant Product Docs

- `docs/product/v14_roadmap.md`
- Nghị định 125/2020/NĐ-CP (Tax violation administrative penalties)

## Acceptance Criteria

- [x] Implement GDT compliance checks: blacklisted MST detection, signature delays, cash payments, template/serial verification, sequence gaps.
- [x] Calculate consolidated T-Score (0 to 100) using weighted scoring models.
- [x] Expose endpoint `POST /api/audit/simulate` to trigger simulated audit runs.
- [x] Render visual risk flags (Low, Medium, High) in the dashboard lists and offcanvas drawers.
- [x] Write unit tests verifying T-Score calculations for various warning combinations.

## Design Notes

- **Module**: `invoices/audit_simulator.py`.
- **Scoring weight**: Blacklisted supplier (Weight 40), signature delay (Weight 15), cash payment penalty (Weight 20), sequence gaps (Weight 10), template mismatch (Weight 15).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v14_audit_simulator.py` checking weighted T-Score calculations |
| Integration | Simulated audit API registers warnings and stores T-Score correctly in SQLite DB |
