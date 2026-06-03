# Story Specification: US-209 — SEE - Tối ưu hóa Form CRO Phát hành & Đăng nhập

## 📋 Context & Business Value
Form Phát hành Hóa đơn điện tử và form Đăng nhập là các điểm thu thập thông tin nhạy cảm và dễ xảy ra lỗi nhập liệu nhất. Áp dụng các nguyên lý Tối ưu hóa Tỷ lệ Chuyển đổi (Form CRO - Conversion Rate Optimization) sẽ giúp giảm thiểu rủi ro nhập sai thông tin, tạo động lực thị giác mượt mà và giúp nhân viên kế toán hoàn thành công việc nhanh chóng hơn.

---

## 🎯 Acceptance Criteria

### 1. Form CRO & Focus States
- Thiết kế trạng thái focus (`:focus` và `:focus-within`) cho các ô nhập liệu (`input`, `select`) thật nổi bật và bắt mắt (ví dụ: viền phát sáng nhẹ màu vàng chanh hoặc xanh rừng, kết hợp đổ bóng nhỏ).
- Tự động định vị con trỏ (autofocus) vào ô nhập liệu đầu tiên khi tải trang.

### 2. Validation & Tooltips
- Tích hợp thông báo lỗi validation trực quan ngay dưới các ô nhập liệu khi có lỗi (ví dụ: đỏ viền nhẹ, thông báo chữ đỏ nhỏ nhấp nháy hoặc hiệu ứng rung nhẹ).
- Hỗ trợ xem mật khẩu (Password visibility toggle) cực mượt với icon thay đổi giữa mắt nhắm và mắt mở.

### 3. Step Flow Guidance
- Làm nổi bật tiến trình 3 bước của form phát hành hóa đơn bằng màu sắc đồng bộ, giúp người dùng luôn định vị được bước hiện tại của mình.

---

## 🛠️ Verification & Test Plan

- **Manual Verification**:
  - Truy cập `/issue_invoice` và `/login`. Kiểm tra các trạng thái hover, focus, và nhập thử dữ liệu để xem các thông báo validation hoạt động thế nào.
  - Test nút ẩn/hiện mật khẩu trên màn hình đăng nhập.
- **Automated Verification**:
  - Đảm bảo các test case liên quan đến login (`tests/test_auth.py`) và issue invoice (`tests/test_invoices.py`) vẫn chạy chính xác.
