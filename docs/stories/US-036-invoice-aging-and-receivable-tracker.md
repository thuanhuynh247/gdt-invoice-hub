# US-036: Theo Dõi Tuổi Hóa Đơn & Kiểm Soát Công Nợ (Invoice Aging Tracker)

## Status

completed

## Lane

normal

## Epic

E34

## Risk Flags

- Public contracts (new `/api/aging/*` endpoints)
- Existing behavior (đọc từ bảng `Invoice` đã có)
- Data model (thêm `due_date`, `paid_date` field vào `Invoice`)

**Risk score: 3 flags → Normal lane with stronger validation**

## Problem Statement

Kế toán hiện không có cách nào theo dõi:
- Hóa đơn **bán ra** nào chưa được thanh toán và đã quá hạn bao nhiêu ngày
- Phân nhóm công nợ theo aging bucket: 0-30, 31-60, 61-90, >90 ngày
- Tổng giá trị công nợ cần thu theo từng nhóm tuổi
- Cảnh báo các hóa đơn quá hạn > 90 ngày

## Product Contract

Hệ thống sẽ cung cấp module **Invoice Aging** trong tab Analytics Pro:

### 1. Thiết Lập Thông Tin Thanh Toán
- Thêm field `due_date` (YYYY-MM-DD) và `paid_date` (YYYY-MM-DD, nullable) vào model `Invoice`
- UI cho phép nhập/cập nhật `due_date` và `paid_date` trong Invoice Edit Modal

### 2. Phân Tích Tuổi Hóa Đơn (Aging Analysis)
Tính `age_days = TODAY - invoice.date` (hoặc `TODAY - due_date` nếu có) cho các hóa đơn:
- `invoice_type = "sold"` (bán ra)
- `is_cancelled = False`
- `paid_date IS NULL` (chưa thanh toán)

Phân nhóm aging buckets:
- **Bucket 0**: Chưa đến hạn (due_date > today)
- **Bucket 1**: 1–30 ngày quá hạn
- **Bucket 2**: 31–60 ngày quá hạn
- **Bucket 3**: 61–90 ngày quá hạn
- **Bucket 4**: > 90 ngày quá hạn (Nguy cơ mất nợ)

### 3. Báo Cáo Aging Summary
Trả về tổng `amount_before_tax` và số lượng hóa đơn theo từng bucket và theo từng khách hàng (`buyer_name`/`buyer_mst`)

### 4. Dashboard Aging
- Bảng tổng hợp: Khách hàng × Bucket × Tổng tiền
- Highlight đỏ các bucket > 60 ngày
- Export to Excel

## Relevant Product Docs

- `invoices/models.py` — thêm `due_date`, `paid_date` columns vào `Invoice`
- `invoices/routes.py` — thêm `/api/aging/` endpoints
- `templates/invoices.html` — thêm sub-tab "Công nợ" trong Analytics Pro tab
- `static/js/main.js` — aging table render
- `docs/TEST_MATRIX.md` — thêm F34

## API Endpoints

### `GET /api/aging/summary`
- Params: `as_of` (YYYY-MM-DD, default: today)
- Query `Invoice` where `invoice_type=sold`, `is_cancelled=False`, `paid_date IS NULL`
- Tính `age_days = as_of - date` (days)
- Group by bucket (0-30, 31-60, 61-90, >90)
- Trả về: `{buckets: [{label, count, total_amount, invoices: [...]}]}`

### `PATCH /api/invoices/<id>/payment`
- Body: `{due_date?: str, paid_date?: str}`
- Cập nhật `Invoice.due_date` và/hoặc `Invoice.paid_date`
- Trả về `{success: true}`

## Acceptance Criteria

### Backend
1. `Invoice` model có thêm `due_date` và `paid_date` columns (nullable string)
2. `GET /api/aging/summary` trả về 4 buckets đúng với dữ liệu test
3. `age_days` tính từ `invoice.date` nếu `due_date` không có, từ `due_date` nếu có
4. Bucket phân loại: `<=0` = Current, `1-30`, `31-60`, `61-90`, `>90`
5. `PATCH /api/invoices/<id>/payment` cập nhật đúng field
6. Hóa đơn có `paid_date` không xuất hiện trong aging report
7. Tất cả endpoints auth protected

### Frontend
8. Sub-tab "📋 Công nợ" hiển thị trong Analytics Pro
9. Bảng aging: cột Khách hàng, Chưa đến hạn, 1-30, 31-60, 61-90, >90, Tổng
10. Tổng row cuối bảng aggregate tất cả khách hàng
11. Highlight màu đỏ bucket >90 ngày
12. Button "Đánh dấu đã TT" trên mỗi hóa đơn trong detail view

## Validation

| Layer | Expected Proof |
| --- | --- |
| Unit | `tests/test_aging.py`: test bucket classification, age_days calculation, paid invoices excluded, summary totals |
| Integration | Auth protection, `PATCH` payment update, aging with mixed due dates |
| UI/Manual | Open Aging sub-tab, verify buckets, mark as paid, verify invoice disappears from aging |

## Data Model Delta

```python
# Thêm vào Invoice model:
due_date = db.Column(db.String(20), nullable=True)    # Ngày đến hạn
paid_date = db.Column(db.String(20), nullable=True)    # Ngày thanh toán thực tế
```

Migration strategy: SQLAlchemy auto-creates nullable columns via `db.create_all()` with `checkfirst=True` — no manual migration needed (existing pattern).

## Harness Delta

- Thêm hàng **F34** vào `docs/TEST_MATRIX.md`
- Thêm **E34** vào `docs/stories/backlog.md`
- Cập nhật `invoices/models.py` (Invoice schema)
- Tạo `tests/test_aging.py` với >= 7 test cases

## Implementation Notes

- `as_of` date mặc định = ngày hiện tại (server-side Vietnam timezone UTC+7)
- Nếu `due_date` chưa set, dùng `invoice.date + 30 ngày` làm due date ước tính
- Export Excel aging report: dùng `openpyxl` (đã có trong requirements)
- Bucket "Current" chỉ hiển thị khi `due_date` đã được set rõ ràng
