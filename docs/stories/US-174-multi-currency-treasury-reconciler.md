# US-174 Multi-Currency Treasury Reconciler

## Status

implemented

## Lane

normal

## Product Contract

The application must retrieve daily exchange rates from Vietcombank (VCB) and automatically convert foreign currency invoices (USD, EUR) to statutory VND amounts based on the transaction date's exchange rate.

## Relevant Product Docs

- `docs/product/v14_roadmap.md`
- Circular 200/214/TT-BTC (Vietnamese Accounting Standards - Foreign currency conversions)

## Acceptance Criteria

- [x] Connect the treasury model with the local VCB Exchange Rate scraper/database.
- [x] Implement daily rate lookup matching the invoice issue date.
- [x] Auto-calculate converted VND amounts for foreign currency invoices using standard transfer rates.
- [x] Display transaction rate and original currency next to converted VND values on the UI.
- [x] Write unit tests verifying currency conversions across historical dates using mock exchange rate tables.

## Design Notes

- **Module**: `invoices/currency_reconciler.py`.
- **Exchange rate types**: Buying rate for receivables (hóa đơn đầu ra), Transfer/Selling rate for payables (hóa đơn đầu vào).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v14_currency_reconciler.py` verifying date-matching lookup |
| Integration | Ingestion of a USD invoice auto-calculates VND based on the VCB database record |
