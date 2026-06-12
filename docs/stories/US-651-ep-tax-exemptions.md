# Spec: US-651 — EP Tax Exemption & Green Transition Auditor

## Status

planned

## Lane

normal

## Product Contract

The system audits Environmental Protection (EP) Tax exemptions and exclusions under Law 57/2010/QH12, ensuring that certified biodegradable materials, coal for electricity production or direct export, and transit/re-export fuels correctly receive 100% exemptions.

## Acceptance Criteria

- [ ] Support 100% exemption for plastic bags with certified biodegradable status.
- [ ] Support 100% exemption for coal used directly for electricity generation or coal directly exported by miners.
- [ ] Support 100% exemption for fuels used in transit or temporarily imported for re-export.
- [ ] Log the audit reason and exemption status accurately in the respective tenant database logs.

## Validation

- `tests/test_v53_features.py::test_biodegradable_exemption`
- `tests/test_v53_features.py::test_coal_electricity_exemption`
- `tests/test_v53_features.py::test_fuel_reexport_exemption`
