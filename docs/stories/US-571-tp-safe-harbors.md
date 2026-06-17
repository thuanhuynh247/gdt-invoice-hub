# Spec: US-571 — Decree 132 Transfer Pricing Safe Harbor & APA Auditor Engine

## Status

planned

## Lane

normal

## Product Contract

The system provides a transfer pricing auditor engine under Decree 132/2020/NĐ-CP. It evaluates taxpayer eligibility for Safe Harbor rules to exempt them from preparing Transfer Pricing Local and Master Files, and tracks compliance with Advance Pricing Agreement (APA) terms.

## Acceptance Criteria

- [ ] Create `tp_safe_harbor_assessments` and `apa_margin_compliance` tables in tenant databases.
- [ ] Evaluate Safe Harbor eligibility: revenue < 50B VND and related-party transactions < 30B VND.
- [ ] Evaluate alternative Safe Harbor: revenue < 200B VND and Net Profit Margin (NPM) exceeds industry minimums (2% trading, 10% manufacturing, 15% services).
- [ ] Ingest APA terms and verify if actual profit margins fall within the agreed interquartile margin ranges.
- [ ] Flag compliance warning statuses: "Eligible" (Safe Harbor met), "Ineligible" (requires TP files), "APA Compliant", or "APA Non-Compliant".

## Validation

- `tests/test_v45_features.py::test_tp_safe_harbors`
