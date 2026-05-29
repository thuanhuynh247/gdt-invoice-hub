# US-151 Interactive Scenario Simulator

## Status

planned

## Lane

normal

## Product Contract

The application must provide a stateless simulation interface that allows financial controllers to stress-test cash-flow projections by adjusting payment delay parameters and invoice rejection rates. The simulator recalculates projections dynamically without modifying actual invoice records.

## Relevant Product Docs

- `docs/product/v12_roadmap.md`

## Acceptance Criteria

- [ ] Implement API endpoint `POST /api/finance/simulate` accepting scenario parameters (delay_days, rejection_rate).
- [ ] Create interactive UI with sliders for payment delay (+15, +30, +60 days) and rejection toggles.
- [ ] Dynamically update SVG cash-flow chart in real-time as user adjusts parameters.
- [ ] Ensure simulation is stateless — no database modifications unless user explicitly confirms.
- [ ] Write tests validating calculation correctness under various scenario configurations.

## Design Notes

- **API**: Stateless POST endpoint returning recalculated projection arrays.
- **UI**: JavaScript sliders and toggles bound to API calls with debounced updates.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Verify simulation engine returns correct adjusted projections |
| Integration | Verify UI correctly renders updated charts on parameter change |
