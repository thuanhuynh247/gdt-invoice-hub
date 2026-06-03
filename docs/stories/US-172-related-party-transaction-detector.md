# US-172 Related Party Transaction Detector

## Status

implemented

## Lane

normal

## Product Contract

The application must identify and flag related-party transactions (giao dịch liên kết) based on equity, shareholding, or transaction threshold rules under Nghị định 132/2020/NĐ-CP.

## Relevant Product Docs

- `docs/product/v14_roadmap.md`
- Nghị định 132/2020/NĐ-CP (Transfer pricing regulations)

## Acceptance Criteria

- [x] Support marking business partners as related-parties (affiliated entity flags) in the Partner Directory.
- [x] Implement value aggregation engine checking if total transaction values cross statutorily regulated thresholds.
- [x] Add warning badges to related-party invoices indicating CIT deduction rules (e.g. EBITDA interest caps).
- [x] Expose endpoint `GET /api/transfer-pricing/transactions` returning aggregated transactional charts.
- [x] Test detecting related-party transactions and applying EBITDA interest limitation alerts.

## Design Notes

- **Module**: `invoices/transfer_pricing.py` related party detector.
- **Rule check**: EBITDA-based interest cap warning if interest expense is recorded.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v14_tp_detector.py` verifying aggregation and alert triggers |
| Integration | Partner details update successfully saves the related-party metadata |
