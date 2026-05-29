# US-034: Phân Tích Xu Hướng Giá Nhà Cung Cấp & Dự Báo Thuế GTGT

## Status

completed

## Lane

normal

## Epic

E32

## Product Contract

Hệ thống sẽ cung cấp hai công cụ phân tích nâng cao kết hợp trong tab **Analytics Pro**:

### 1. Phân Tích Xu Hướng Giá & So Sánh Nhà Cung Cấp (Supplier Price Analytics)
Theo dõi biến động đơn giá của cùng một tên mặt hàng theo thời gian và giữa các nhà cung cấp khác nhau. Giúp bộ phận mua hàng:
- Phát hiện biến động giá bất thường (>20% so với giá trung bình lịch sử)
- So sánh nhà cung cấp rẻ nhất theo mặt hàng trong kỳ
- Hiển thị biểu đồ đường (Line/Bar SVG) xu hướng giá theo thời gian

### 2. Dự Báo Thuế GTGT & Dòng Tiền (VAT Forecasting)
Dự báo số thuế GTGT phải nộp cho kỳ tiếp theo dựa trên xu hướng lịch sử:
- Tính thuế GTGT đầu ra − đầu vào được khấu trừ theo từng tháng trong năm hiện tại
- Tính tốc độ tăng trưởng trung bình (CAGR-like trend) để chiếu dự báo 2-3 tháng tiếp theo
- Hiển thị cảnh báo nếu số thuế dự kiến tăng >30% so với kỳ trước
- Biểu đồ cột SVG hiển thị thực tế vs. dự báo

## Relevant Product Docs

- `docs/ARCHITECTURE.md`
- `invoices/routes.py`
- `invoices/models.py` (Invoice, LineItem)
- `templates/invoices.html`
- `static/js/main.js`

## Acceptance Criteria

### Backend

1. **`GET /api/analytics/supplier-price-trends`**
   - Params: `item_name` (bắt buộc, tìm kiếm case-insensitive), `year` (tùy chọn)
   - Nhóm `LineItem` theo `item_name` LIKE, lấy từng `invoice.date` → tháng, `unit_price`, `seller_name`, `seller_mst`
   - Tính `avg_price`, `min_price`, `max_price`, `anomaly` (True nếu unit_price > avg * 1.20)
   - Trả về: danh sách tháng × nhà cung cấp × giá
   - Auth protected bởi `_ensure_logged_in()`

2. **`GET /api/analytics/top-items`**
   - Trả về danh sách top 20 tên mặt hàng phổ biến nhất (distinct, sorted by count) để drive autocomplete
   - Auth protected

3. **`GET /api/analytics/vat-forecast`**
   - Params: `year` (mặc định năm hiện tại)
   - Tính tháng 1–12: `output_vat` (sold), `input_vat` (purchase), `net_vat = output - input`
   - Dự báo 2 tháng tiếp theo bằng linear trend (avg delta of last 3 actual months)
   - Flag `warning: true` nếu dự báo tháng kế tiếp > tháng hiện tại * 1.30
   - Trả về JSON gồm `actual[]` và `forecast[]`
   - Auth protected

### Frontend (Tab `#analytics-pro-tab`)

4. **Supplier Price Trends Panel**:
   - Input autocomplete (driven bởi `/api/analytics/top-items`) để chọn mặt hàng
   - SVG Line Chart hiển thị giá theo tháng theo nhà cung cấp (mỗi vendor 1 màu riêng)
   - Bảng so sánh nhà cung cấp: tên, MST, số lần mua, giá TB, giá min/max, cảnh báo bất thường

5. **VAT Forecast Panel**:
   - Biểu đồ cột SVG: thực tế (xanh ngọc) vs. dự báo (cam gradient)
   - Badge cảnh báo nếu `warning: true`
   - Hiển thị số: Thuế đầu ra, Thuế đầu vào, Số thuế phải nộp dự báo

## Validation

| Layer | Expected Proof |
| --- | --- |
| Unit | `tests/test_analytics.py`: test `/api/analytics/supplier-price-trends`, `/api/analytics/top-items`, `/api/analytics/vat-forecast` với dữ liệu mock |
| Integration | Auth protection, aggregation correctness, forecast logic |
| UI/Manual | Toggle tab Analytics Pro, chọn mặt hàng, kiểm tra chart SVG render |

## Harness Delta

- Thêm hàng **F32** vào `docs/TEST_MATRIX.md`
- Thêm **E32** vào `docs/stories/backlog.md`
- Cập nhật `PROGRESS_TRACKER_INVOICE_WEBAPP.md`
