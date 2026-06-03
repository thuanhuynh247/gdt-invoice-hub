# US-018: HTTT Extraction & 5M VND Non-Cash Audit Compliance Rule

## Status

implemented

## Lane

normal

## Product Contract

The system must automatically parse the payment method from incoming electronic invoice XML files and raise a smart audit warning if the transaction value is 5 million VND or above but recorded as cash, highlighting potential VAT deduction non-compliance under the new VAT Law 2024.

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)
- [docs/product/invoices.md](file:///d:/LearnAnyThing/Webapp%20XML/docs/product/invoices.md)

## Acceptance Criteria

- [x] XML parser extracts the payment method from `<HTTToan>` or `<htttoan>` tags.
- [x] Local database stores this payment method as `payment_method`.
- [x] Smart Audit engine runs a 6th rule verifying that any invoice with a total amount >= 5,000,000 VND does not list cash payment methods (e.g. `TM`, `tiền mặt`, `cash`).
- [x] Details drawer UI displays the extracted payment method in a "Hình thức TT" label.
- [x] Green "Valid" summary alert in Details Drawer updates to mention 6 smart audit tests.
- [x] Excel export engine includes "Hình thức thanh toán" as a column in the audited invoices sheet.
- [x] Unit tests cover all branches: amount >= 5M with TM, amount >= 5M with CK, amount < 5M with TM.


## Design Notes

- **API**: `/api/invoices/<invoice_id>/details` will now return `"payment_method"`.
- **Database**: Each record in `invoices_db.json` will contain `"payment_method"`.
- **Domain Rules**: Threshold is `5000000.0`. Cash checks are case-insensitive and partial match for `tm`, `tiền mặt`, `cash`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `tests/test_meinvoice.py` test_payment_method_audit verification |
| Integration | `scripts/validate.bat` run successfully |

## Harness Delta

None.
