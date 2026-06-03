# Story Specification: US-210 — RUN - Rà soát Captcha Solver, Archiver & Nâng cấp Pytest Suite

## 📋 Context & Business Value
Việc tự động hóa tải và giải Captcha đóng vai trò tối quan trọng đối với khả năng đồng bộ dữ liệu hóa đơn tự động từ Tổng cục Thuế. Đồng thời, cơ chế lưu trữ hóa đơn lạnh (Cold Storage Archiver) giúp duy trì hiệu năng của hệ thống SQLite chính trong dài hạn. Để đảm bảo tính bền vững của các thành phần này, chúng ta cần rà soát độ ổn định của Captcha Solver, Archiver và nâng cấp Pytest suite để chạy ổn định, nhanh chóng.

---

## 🎯 Acceptance Criteria

### 1. Robust Captcha Solver & Fallback
- Đảm bảo Captcha Solver hoạt động ổn định ngoại tuyến bằng `ddddocr`. Lọc bỏ nhiễu vector SVG và sắp xếp các đường vẽ ký tự từ trái qua phải theo đúng thứ tự.
- Xử lý mượt mà trường hợp `ddddocr` hoặc `svglib` ném lỗi ngoại lệ để không làm sập luồng đồng bộ, tự động chuyển về cơ chế load lại Captcha.

### 2. Archiver Testing
- Đảm bảo dữ liệu cũ trên 5 năm được nén định dạng zip lưu vào `data/archives` thành công, đồng thời xóa sạch dữ liệu cũ khỏi SQLite nhưng vẫn hỗ trợ tìm kiếm hợp nhất (Search merged active & cold storage) bình thường mà không gây downtime.

### 3. Fast and Non-Blocking Test Suite
- Skip bài test Selenium E2E UI khi không chạy ở chế độ UI test (`RUN_E2E!=1`) để tránh tình trạng test suite bị treo vô hạn.
- Đảm bảo toàn bộ 448+ test cases trong Pytest suite chạy thành công dưới 70 giây.

---

## 🛠️ Verification & Test Plan

- **Automated Verification**:
  - Chạy `scripts/harness validate --cmd "venv/Scripts/python -m pytest"` để kiểm tra toàn bộ suite.
  - Xác nhận tất cả test suite chạy hoàn tất thành công.
