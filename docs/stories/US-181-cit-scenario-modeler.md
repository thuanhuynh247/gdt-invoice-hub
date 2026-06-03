# US-181 CIT Scenario Modeler & Stress-Tester

## Status

implemented

## Lane

normal

## Product Contract

The application must provide an interactive what-if modeling panel allowing users to adjust financial variables (revenue forecasts, interest expenses, salary structures, R&D credits) and dynamically calculate the simulated CIT liability, effective tax rate, and tax compliance score.

## Relevant Product Docs

- `docs/product/v15_roadmap.md`

## Acceptance Criteria

- [x] Build a frontend visual dashboard with slider controls for custom financial simulation inputs.
- [x] Implement mathematical recalculation of CIT liability and effective tax rate in real-time.
- [x] Provide warning messages when simulated variables breach statutory tax guidelines (e.g. loan interest exceeding 30% of EBITDA).
- [x] Support saving and comparing multiple named scenarios (e.g., Conservative vs. Optimistic).
- [x] Expose API endpoint `POST /api/cit/simulate-scenario` to run calculations.

## Design Notes

- **Module**: `invoices/cit_modeler.py` and frontend UI component.
- **Data storage**: Saves scenario profiles in `instance/cit_scenarios.json` or taxpayer database.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v15_cit_modeler.py` verifying real-time CIT recalculations on inputs |
| Integration | API endpoint `POST /api/cit/simulate-scenario` processes scenario metrics and returns correct math outputs |
