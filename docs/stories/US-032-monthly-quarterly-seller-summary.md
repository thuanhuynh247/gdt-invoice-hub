# US-032: Bảng Kê Tổng Hợp Hóa Đơn Đầu Vào Theo Tháng/Quý Và Đối Tác (Input Invoice Summary by Month/Quarter and Partner)

## Status

implemented

## Lane

normal

## Product Contract

The application will implement a monthly and quarterly input invoice aggregation matrix grouped by sellers (issuers) to help users compile monthly/quarterly input tax sheets (bảng kê hóa đơn đầu vào) for financial auditing and tax checking.

Specifically:
1. **Aggregation metrics**: For each Month (e.g. `05/2026`) or Quarter (e.g. `Quý 2/2026`), list unique sellers with their total invoices, total value before tax, total tax amount, and total aggregate payment value.
2. **Interactive selection**: Allow filtering by Year and toggling views between "Theo Tháng" (Monthly) and "Theo Quý" (Quarterly).
3. **Accordion/Grouped Interface**: Render a premium Supabase glassmorphic collapsible structure where expanding each period shows a sleek sub-table containing issuer spend details.

## Relevant Product Docs

- `docs/ARCHITECTURE.md`
- `invoices/routes.py`
- `templates/invoices.html`
- `static/js/main.js`
- `docs/stories/backlog.md`
- `PROGRESS_TRACKER_INVOICE_WEBAPP.md`

## Acceptance Criteria

1. **REST API Endpoint `/api/invoices/summary-by-seller` (GET)**:
   - Accept parameters: `period_type` (`monthly` or `quarterly`) and `year` (e.g. `2026` or empty for all).
   - Group invoices by their year-month and seller tax code (`seller_mst`/`seller_name`).
   - Sum metrics: `invoice_count` (count), `total_before_tax` (sum of amount_before_tax), `total_tax` (sum of tax_amount), and `total_amount` (sum of total_amount).
   - Sort periods descending (latest period first) and sort sellers within each period descending by total spend.
   - Secure route using `_ensure_logged_in()`.

2. **Frontend UI Switcher inside Partner tab**:
   - Add a premium HSL button-group toggle at the top of the Partners tab: "Tất Cả Đối Tác" vs "Bảng Kê Tổng Hợp Đầu Vào".
   - Toggle visibility of the default cumulative partner table and the new period-wise aggregated summary container.
   - Include period type selectors (`monthly` vs `quarterly`) and a select box for filtering by Year.

3. **Grouped Period Cards & Tables**:
   - Render periods dynamically using collapsible glassmorphic accordions.
   - Under each period card, display a summary of period totals (Total before tax, Total tax, Total spend).
   - Expanding a card renders a neat table containing:
     - Tên doanh nghiệp (Seller Name)
     - Mã số thuế (Tax Code)
     - Số lượng HĐ (Invoice count)
     - Tiền trước thuế (Before-tax amount)
     - Tiền thuế GTGT (Tax amount)
     - Tổng thanh toán (Total paid value)

## Design Notes

### 1. API Output Structure
```json
{
  "success": true,
  "period_type": "monthly",
  "year": "2026",
  "data": [
    {
      "period": "Tháng 05",
      "total_before_tax": 100000000.0,
      "total_tax": 10000000.0,
      "total_amount": 110000000.0,
      "sellers": [
        {
          "seller_mst": "0109988776",
          "seller_name": "CÔNG TY TNHH THƯƠNG MẠI AN PHÁT",
          "invoice_count": 4,
          "total_before_tax": 60000000.0,
          "total_tax": 6000000.0,
          "total_amount": 66000000.0
        }
      ]
    }
  ]
}
```

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit / Integration | Write `tests/test_summary_by_seller.py` verifying `/api/invoices/summary-by-seller` parameter filters, database grouping, and aggregation correctness. |
| UI/Manual | Toggle "Bảng Kê Tổng Hợp Đầu Vào" tab sub-view, expand monthly lists, and verify matched financial figures. |

## Harness Delta

- Update `docs/stories/backlog.md` and `docs/TEST_MATRIX.md` to map US-032.
- Update `PROGRESS_TRACKER_INVOICE_WEBAPP.md` with new checkmarks.
