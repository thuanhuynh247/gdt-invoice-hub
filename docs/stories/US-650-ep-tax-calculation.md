# Spec: US-650 — Core EP Tax Calculation Engine

## Status

planned

## Lane

normal

## Product Contract

The system classifies taxable environmental items (fuels, coal, plastic bags, chemicals) and calculates the Environmental Protection (EP) Tax using absolute tax-per-unit rates under Nghị quyết số 19/2026/QH16 / Nghị quyết số 109/2025/UBTVQH15 and Luật Thuế bảo vệ môi trường.

## Acceptance Criteria

- [ ] Create `ep_tax_fuel_logs`, `ep_tax_coal_logs`, `ep_tax_plastic_bag_logs`, and `ep_tax_chemical_logs` tables in tenant databases.
- [ ] Calculate fuel EP tax using rates: Petrol = 2,000 VND/l, Diesel = 1,000 VND/l, Kerosene = 600 VND/l.
- [ ] Calculate coal EP tax by type: Lignite/Sub-bituminous = 20,000 VND/tonne, Anthracite = 30,000 VND/tonne, Other coal = 15,000 VND/tonne.
- [ ] Calculate non-biodegradable plastic bags EP tax at 50,000 VND/kg.
- [ ] Calculate HCFC chemical EP tax at 5,000 VND/kg.

## Validation

- `tests/test_v53_features.py::test_fuel_ep_tax`
- `tests/test_v53_features.py::test_coal_ep_tax`
- `tests/test_v53_features.py::test_plastic_bag_ep_tax`
- `tests/test_v53_features.py::test_chemical_ep_tax`
