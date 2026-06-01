# Story Specification: US-208 — SEE - Vẽ biểu đồ dòng tiền SVG chuyển sắc

## 📋 Context & Business Value
Tính năng Dự báo dòng tiền thông minh giúp doanh nghiệp đánh giá tính thanh khoản trong tương lai 30/60/90 ngày. Để tăng cường tính trực quan và mang lại vẻ đẹp chuẩn Wise Fintech Aesthetic, biểu đồ dòng tiền cần được cải tiến sử dụng đường nét mượt mà (smooth cubic curve), tô màu gradient chuyển sắc cho phần diện tích dưới đường biểu đồ (area gradient fill) và hiệu ứng tương tác hover hiện tooltip thông minh khi rê chuột vào các điểm dữ liệu chính.

---

## 🎯 Acceptance Criteria

### 1. Gradient Area Chart Fill
- Thay thế đường thẳng gấp khúc (`polyline`) thô ráp bằng đường cong mềm mại (`path` với lệnh bezier `C` hoặc thuật toán vẽ spline mượt mà).
- Thêm một thẻ `<path>` tô màu gradient chuyển sắc mờ (opacity) từ màu xanh dương sang tím/trong suốt phía dưới đường dòng tiền để tạo chiều sâu trực quan.

### 2. Interactive Tooltips & Peaks
- Khi rê chuột (hover) qua các điểm mốc trên biểu đồ (mỗi 10 ngày hoặc các điểm cực trị), hiển thị một tooltip nhỏ hiển thị ngày và số dư dự kiến chính xác tại điểm đó.
- Tạo điểm nhấn thị giác (pulsing dot) cho các ngày có dòng tiền ròng thấp kỷ lục hoặc âm.

### 3. Grid Enhancements
- Thiết kế lại các đường lưới (grid lines) mờ mịn, đảm bảo hiển thị rõ ràng trục số 0 (Zero axis) khi dòng tiền xuống mức âm.

---

## 🛠️ Verification & Test Plan

- **Manual Verification**:
  - Truy cập trang `/cashflow` (Dự báo dòng tiền) và kéo các thanh trượt tham số What-If.
  - Xác nhận biểu đồ vẽ lại ngay lập tức với các đường cong mượt mà và vùng gradient chuyển sắc hoạt động chính xác.
  - Rê chuột vào các điểm mốc và kiểm tra xem tooltip hiển thị đúng thông tin.
- **Automated Verification**:
  - Đảm bảo endpoint mô phỏng `/api/finance/simulate` vẫn hoạt động tốt, trả về cấu trúc JSON đúng chuẩn.
