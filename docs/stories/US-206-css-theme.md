# Story Specification: US-206 — Tái cấu trúc CSS hệ thống và Theme Switcher

## 📋 Context & Business Value
Hệ thống Hub hóa đơn cần một diện mạo nhất quán, mượt mà và sang trọng theo phong cách Wise Fintech Aesthetic. Việc chuyển đổi giữa chế độ Light và Dark phải diễn ra tức thì, không bị nhấp nháy (flicker) và có các hiệu ứng chuyển động vi mô (micro-animations) mượt mà cho các nút bấm và thành phần giao diện.

---

## 🎯 Acceptance Criteria

### 1. Centralized Theme Styles & Variables
- Tối ưu hóa các biến CSS trong `:root` và `[data-theme="dark"]` để đảm bảo độ tương phản cao, màu sắc dịu mắt.
- Định nghĩa lại các màu sắc đặc trưng của phong cách Fintech: xanh rừng (Forest Green), vàng chanh (Lime), các tông xám mịn và hiệu ứng Glassmorphism.

### 2. Smooth Transitions & Micro-animations
- Đăng ký hiệu ứng transition mượt mà (`0.3s ease-in-out` hoặc `cubic-bezier`) cho tất cả các thuộc tính liên quan đến đổi theme: `background-color`, `color`, `border-color`, `box-shadow`.
- Đảm bảo theme switcher button có hiệu ứng xoay nhẹ và đổi icon mượt mà khi click.

### 3. Base HTML Compliance
- Kiểm tra và đảm bảo không có mã CSS inline nào xung đột với các lớp tiện ích của thiết kế hệ thống.
- Ngăn chặn hoàn toàn hiện tượng nhấp nháy giao diện khi tải trang (đã có đoạn mã kiểm tra trong thẻ `<head>` của `base.html`).

---

## 🛠️ Verification & Test Plan

- **Manual Verification**:
  - Click vào nút Theme Switcher ở góc phải Navbar và kiểm tra sự thay đổi của biến màu CSS trên toàn trang.
  - Kiểm tra xem icon nút bấm thay đổi đúng từ biểu tượng Mặt trời sang Mặt trăng và ngược lại.
- **Automated Verification**:
  - Chạy smoke tests và E2E (nếu được kích hoạt) để đảm bảo không có phần tử giao diện nào bị lỗi CSS hoặc vỡ khung.
