# Spec: US-533 — Form 01/ĐNHT Refund Packet Wizard

## Status

planned

## Lane

normal

## Product Contract

The system provides a step-by-step wizard to compile the official export VAT tax refund application form (Giấy đề nghị hoàn trả mẫu 01/ĐNHT) per Circular 80/2021/TT-BTC.

## Acceptance Criteria

- [ ] Support calculation of cumulative input tax credits and allocated export VAT refund requests.
- [ ] Implement `VatRefundApplication` database model to save drafts and submissions.
- [ ] Provide user inputs for bank details, refund reasons, and compliance checkpoints.
- [ ] Auto-validate that the refund request amount does not exceed the allowed threshold (10% of export revenue or 300 million VND).

## Validation

- `tests/test_v41_features.py::test_form_01_dnht_wizard`
