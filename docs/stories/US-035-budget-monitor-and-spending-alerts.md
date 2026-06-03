# US-035: Giám Sát Ngân Sách & Cảnh Báo Chi Tiêu Theo Tháng

## Status

completed

## Lane

normal

## Epic

E33

## Risk Flags

- Public contracts (new API shape `/api/budget/*`)
- Data model (new `BudgetConfig` table)
- Existing behavior (tích hợp vào Analytics Pro tab đã có)

**Risk score: 3 flags → Normal lane with stronger validation**

## Problem Statement

Hiện tại kế toán chỉ xem được chi tiêu thực tế sau khi hóa đơn đã nhập vào kho. Không có cơ chế nào cho phép:
- Đặt ngân sách giới hạn chi tiêu theo tháng (theo nhà cung cấp hoặc danh mục)
- Nhận cảnh báo tự động khi chi tiêu vượt ngưỡng 80% / 100% ngân sách
- So sánh chi tiêu thực tế vs. kế hoạch trong biểu đồ trực quan

## Product Contract

Hệ thống sẽ cung cấp module **Budget Monitor** trong tab Analytics Pro:

### 1. Thiết Lập Ngân Sách (Budget Configuration)
- Kế toán nhập giới hạn chi tiêu theo tháng cho từng **danh mục chi phí** (expense_category) hoặc **nhà cung cấp** (seller_mst)
- Cấu hình được lưu persistent trong `SystemConfig` (key-value JSON)
- Giao diện: Form trong Analytics Pro sub-tab "Ngân sách"

### 2. Theo Dõi Thực Tế vs. Kế Hoạch
- Tính tổng chi tiêu thực tế trong tháng hiện tại từ bảng `LineItem` (group by expense_category)
- Tính % sử dụng ngân sách: `(actual / budget) * 100`
- Trạng thái màu: 
  - Xanh lá: < 70%
  - Vàng: 70–100%  
  - Đỏ: > 100% (vượt ngân sách)

### 3. Cảnh Báo Tự Động
- Hiển thị badge cảnh báo ⚠ khi bất kỳ danh mục nào >= 80% ngân sách
- Toast notification khi user mở tab Budget Monitor (nếu có vi phạm)

### 4. Biểu Đồ So Sánh SVG
- Horizontal bar chart SVG: Danh mục × Thực tế vs. Ngân sách
- Không dùng thư viện bên ngoài — pure SVG (giống F32)

## Relevant Product Docs

- `invoices/models.py` — thêm `BudgetConfig` model (hoặc dùng `SystemConfig` JSON)
- `invoices/routes.py` — thêm `/api/budget/` endpoints
- `templates/invoices.html` — thêm sub-tab "Ngân sách" vào Analytics Pro
- `static/js/main.js` — logic render chart + alert
- `docs/TEST_MATRIX.md` — thêm F33

## API Endpoints

### `GET /api/budget/config`
- Trả về cấu hình ngân sách hiện tại (list of {category, limit_vnd, month})
- Auth protected

### `POST /api/budget/config`
- Body: `{configs: [{category: str, limit_vnd: float, month: str}]}`
- Lưu vào `SystemConfig` key `budget_config_<YYYY-MM>`
- Trả về `{success: true}`

### `GET /api/budget/actuals`
- Params: `month` (YYYY-MM, default: current month)
- Tính tổng `LineItem.amount_before_tax` grouped by `expense_category`
- Join với `Invoice` để filter theo tháng
- Trả về: `[{category, actual_vnd, budget_vnd, pct_used, status}]`

## Acceptance Criteria

### Backend
1. `GET /api/budget/config` trả về danh sách cấu hình, rỗng nếu chưa cấu hình
2. `POST /api/budget/config` lưu cấu hình cho tháng được chỉ định
3. `GET /api/budget/actuals` tính tổng chi tiêu theo danh mục đúng với dữ liệu mẫu
4. `pct_used = actual / limit * 100`, `status` ∈ `{ok, warning, over_budget}`
5. Tất cả endpoints yêu cầu auth (`_ensure_logged_in()`)

### Frontend
6. Sub-tab "📊 Ngân sách" xuất hiện trong Analytics Pro tab
7. Form nhập ngân sách: dropdown danh mục + input số tiền + nút Lưu
8. Horizontal SVG bar chart hiển thị thực tế vs. kế hoạch mỗi danh mục
9. Badge màu đỏ trên tab nếu bất kỳ danh mục nào > 100% ngân sách
10. Toast warning khi open tab và có >= 1 danh mục >= 80%

## Validation

| Layer | Expected Proof |
| --- | --- |
| Unit | `tests/test_budget.py`: test config save/load, actuals aggregation, pct calculation, status logic |
| Integration | Auth protection, month-scoped actuals, JSON config persistence |
| UI/Manual | Open Budget sub-tab, set limits, verify bars render, trigger over-budget state |

## Data Model Delta

```python
# Không cần bảng mới — dùng SystemConfig với key convention:
# budget_config_<YYYY-MM> = JSON list of {category, limit_vnd}
```

## Harness Delta

- Thêm hàng **F33** vào `docs/TEST_MATRIX.md`
- Thêm **E33** vào `docs/stories/backlog.md`
- Tạo `tests/test_budget.py` với >= 8 test cases

## Implementation Notes

- Danh sách danh mục lấy từ `LineItem.expense_category` distinct (giống US-034 top-items pattern)
- Default budget month = tháng hiện tại (UTC+7)
- Nếu chưa cấu hình limit cho danh mục, không hiển thị trong chart
- Dùng `SystemConfig` key-value store (đã có) — không thêm migration
