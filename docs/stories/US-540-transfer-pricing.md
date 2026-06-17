# Spec: US-540 — Transfer Pricing Transaction Ingestion & Benchmark Comparator Engine

## Status

planned

## Lane

normal

## Product Contract

The system ingests related party transactions and compares the taxpayer's profit margin against a simulated arm's length interquartile range (25th to 75th percentile) under Decree 132/2020/NĐ-CP. It calculates CIT adjustments if the margin is below the 25th percentile.

## Acceptance Criteria

- [ ] Implement `RelatedPartyTransaction` and `TransferPricingBenchmark` models in database (`invoices/models.py`).
- [ ] Create benchmarking calculation logic in `invoices/v42_service.py` to:
  - Calculate taxpayer's margin.
  - Determine if it falls within the interquartile range.
  - Apply adjustment to the median of the benchmark range if below the 25th percentile.
- [ ] Return detailed comparison object including original margin, range, adjustment amount, and status.

## Validation

- `tests/test_v42_features.py::test_transfer_pricing_benchmark_calculator`
