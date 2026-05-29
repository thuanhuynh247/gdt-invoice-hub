# US-033: Dự Thảo Tờ Khai Thuế GTGT 01/GTGT & Tối Ưu Hóa Khấu Trừ Thuế Bằng AI (AI-Powered VAT Return Drafter & Tax Deductibility Optimizer)

## Status

completed

## Lane

normal

## Product Contract

The application will construct a regulatory-compliant Vietnamese VAT Declaration Draft (Mẫu 01/GTGT) and an interactive Tax Deductibility Optimizer. This will allow users to compile output sales VAT, calculate eligible input VAT based on smart compliance audit rules, and optimize their final tax balance.

Specifically:
1. **Smart Deductibility Engine**: Aggregated input invoices are split into "Eligible Deductible Input VAT" (Chỉ tiêu [25]) and "Ineligible/Disputed Input VAT" based on smart auditing warning classifications (e.g. Cash payments >= 20M VND, inactive/closed partner MSTs, or missing digital signatures).
2. **Interactive 01/GTGT Tax Form Layout**: Render a pristine, glassmorphic grid recreation of the official Vietnamese VAT Return (Tờ khai thuế GTGT Mẫu 01/GTGT) featuring index keys (`[22]`, `[23]`, `[24]`, `[25]`, `[30]`, `[31]`, `[32]`, `[33]`, `[40]`, `[43]`) populated dynamically by AJAX.
3. **Interactive Adjustments Grid**: List "Disputed Invoices" contributing to the difference between total input VAT (`[24]`) and deductible VAT (`[25]`). Allow users to toggle individual checkboxes to "Force Include" or "Exclude" disputed vouchers, recalculating the final tax payable or carried-forward balance live with smooth transitions.

## Relevant Product Docs

- `docs/ARCHITECTURE.md`
- `invoices/routes.py`
- `templates/invoices.html`
- `static/js/main.js`
- `docs/stories/backlog.md`
- `PROGRESS_TRACKER_INVOICE_WEBAPP.md`

## Acceptance Criteria

1. **REST API Endpoint `/api/reports/vat-declaration` (GET)**:
   - Accept parameters: `period_type` (`monthly` or `quarterly`), `period_value` (e.g., month `05` or quarter `2`), and `year`.
   - Calculate output sales VAT aggregates:
     - Group sold invoices by VAT rates: 0%, 5%, 8%, 10% (mapping to Chỉ tiêu [26], [30], [32]).
   - Calculate input purchase VAT aggregates:
     - Total purchased taxable value (Chỉ tiêu [23]) and total input tax (Chỉ tiêu [24]).
     - Auto-calculate deductible input VAT (Chỉ tiêu [25]): Total input tax *excluding* high-risk invoices (warnings: `cash_payment_limit` >= 20M VND, partner MST `closed`/`inactive`, or missing digital signature).
   - Return calculated tax balance metrics:
     - Chỉ tiêu [40] (VAT payable to State): `max(0, Total Output VAT - Deductible Input VAT)`.
     - Chỉ tiêu [43] (VAT carried forward): `max(0, Deductible Input VAT - Total Output VAT)`.
   - Return the list of high-risk "disputed" invoices with their details and specific compliance warning reasons to let the frontend manage overrides.
   - Secure route using `_ensure_logged_in()`.

2. **Frontend Tab UI (`#tax-return-tab`)**:
   - Add a premium tab button "Tờ Khai & Tối Ưu Thuế" with a custom vector SVG icon next to the BC26 reports tab.
   - Design a gorgeous dashboard selector bar to filter by Month/Quarter, specific Period index, and Year.
   - Display a side-by-side split screen on desktop:
     - **Left panel**: Interactive HTML Vietnamese VAT Declaration form (Mẫu 01/GTGT) with clear, standardized borders, labels, index boxes, and dynamic bindings.
     - **Right panel**: Glassmorphic tax optimizer card displaying the list of disputed invoices. Each item features custom status badges, details of the tax risk, and a toggle switch to manually include/exclude the voucher.
   - Changing any toggle recalculates Chỉ tiêu [25], [40], and [43] instantly on the form using frontend client-side calculation triggers.

## Design Notes

### 1. API Output Structure
```json
{
  "success": true,
  "period_type": "monthly",
  "period_value": "05",
  "year": "2026",
  "outputs": {
    "tax_0": 0.0,
    "tax_5": 0.0,
    "tax_8": 15000000.0,
    "tax_10": 25000000.0,
    "total_output_value": 40000000.0,
    "total_output_vat": 3700000.0
  },
  "inputs": {
    "total_input_value": 50000000.0,
    "total_input_vat": 4500000.0,
    "deductible_input_vat": 2500000.0
  },
  "calculations": {
    "vat_payable_40": 1200000.0,
    "vat_carried_forward_43": 0.0
  },
  "disputed_invoices": [
    {
      "id": "MST_A-C26-0001",
      "number": "0001",
      "date": "2026-05-10",
      "seller_name": "CONG TY A",
      "seller_mst": "0101234567",
      "total_amount": 22000000.0,
      "tax_amount": 2000000.0,
      "warning": "Thanh toán bằng tiền mặt 22 triệu VND (>= 20M VND) vi phạm Luật Thuế GTGT 2024 về thanh toán không dùng tiền mặt."
    }
  ]
}
```

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit / Integration | Write `tests/test_vat_declaration.py` verifying `/api/reports/vat-declaration` formula outputs, exclusions logic, and period aggregations. |
| UI/Manual | Select the VAT Return tab, choose a period, view computed values on Mẫu 01/GTGT, toggle a disputed cash invoice, and check that the State payable tax drops and Chỉ tiêu [25] updates dynamically. |

## Harness Delta

- Update `docs/stories/backlog.md` and `docs/TEST_MATRIX.md` to map US-033.
- Update `PROGRESS_TRACKER_INVOICE_WEBAPP.md` with new checkmarks.
