# Spec: US-553 — OECD Pillar Two Global Minimum Tax (GMT) Estimator

## Status

planned

## Lane

normal

## Product Contract

The system estimates consolidated group ETR and Top-up Tax under OECD Pillar Two GloBE rules across multiple tenant MST databases, factoring in statutory minimum rates and substance-based exclusions.

## Acceptance Criteria

- [ ] Support consolidated estimation across a list of taxpayer tenant profiles (MSTs).
- [ ] Calculate consolidated covered taxes and GloBE income to determine the group ETR.
- [ ] Determine the top-up tax rate (target minimum 15% - group ETR) and apply it to GloBE income after substance-based income exclusion (SBIE).

## Validation

- `tests/test_v43_features.py::test_pillar_two_topup_estimation`
