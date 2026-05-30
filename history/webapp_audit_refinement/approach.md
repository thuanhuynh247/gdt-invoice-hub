# Khuym Approach: Webapp UI/UX Audit and Logic Refinement

Phương pháp triển khai và phân chia các giai đoạn nâng cấp thẩm mỹ giao diện cùng bảo mật nghiệp vụ cho hệ thống GDT Invoice Hub.

---

## 1. Phương pháp & Đánh giá Rủi ro (Approach & Risk Gate)

* **Chế độ Vận hành (Mode)**: `Standard` (Kết hợp cả thay đổi giao diện và kiểm thử logic).
* **Mục tiêu Chứng minh (Proof Needs)**:
  * UI/UX: Các trang chính phải chuyển đổi giao diện sáng/tối mượt mà, bảng biểu thu gọn thông minh trên màn hình hẹp, Bento Grid hiển thị cân đối.
  * Logic: Tỷ lệ giải Captcha tự động ổn định, phân vùng zip lịch sử nén đúng định dạng, cache stats không bị rò rỉ dữ liệu giữa các phiên.
* **Rủi ro Kỹ thuật & Biện pháp**:
  * *Rủi ro*: Sửa đổi CSS toàn cục gây ảnh hưởng tiêu cực đến layout của các trang nhỏ.
  * *Giải pháp*: Sử dụng hệ thống biến CSS toàn cục (CSS custom properties) có kế thừa trong `style.css` để quản lý giao diện tập trung.

---

## 2. Kế hoạch Phân kỳ Giai đoạn (Phase Plan)

### Giai đoạn 1: SEE - Tối ưu hóa UI/UX toàn hệ thống (Glassmorphism & Sleek Theme)
* **Công việc**:
  1. Cấu hình biến CSS cho 2 theme sáng/tối và các lớp nền kính mờ (`.glass-card`, `.glass-navbar`) trong `static/css/style.css`.
  2. Nâng cấp `templates/base.html`: Tinh chỉnh thanh định hướng (Navbar) mượt mà hơn và thêm nút công tắc chuyển màu cao cấp.
  3. Cải tạo `templates/invoices.html`: Chuyển KPI thành Bento Grid chuyển màu mềm mại, làm bảng dữ liệu dạng thẻ (cards) khi xem trên mobile.
  4. Nâng cấp `templates/cashflow.html`: Vẽ biểu đồ dòng tiền trực tiếp bằng thẻ SVG động chuyển màu (gradient paths) thay cho bảng số đơn điệu.
  5. Cải tạo `templates/issue_invoice.html` và `templates/login.html`: Áp dụng Form CRO, tạo viền sáng mịn khi nhấp chuột (focus ring).
* **Tiêu chí Hoàn thành (Exit Gate)**: Trình duyệt subagent chụp ảnh màn hình 100% đạt chuẩn thẩm mỹ cao, chuyển đổi màu theme hoàn hảo.

### Giai đoạn 2: RUN & ORGANIZE - Audit Logic, Bảo mật & Bộ Test tự động
* **Công việc**:
  1. Audit logic tự động giải mã captcha (`captcha_solver.py`), tối ưu hóa biểu thức chính quy tách ký tự SVG.
  2. Rà soát cơ chế lưu trữ phân vùng ZIP lạnh (`invoices/archiver.py`) để bảo đảm nén và giải nén trong phân vùng dữ liệu không hao phí RAM.
  3. Củng cố bộ kiểm thử Pytest: Bổ sung 3 file test chất lượng cao bao quát toàn bộ logic cache, nén zip, giải captcha và các góc khuất bảo mật.
* **Tiêu chí Hoàn thành (Exit Gate)**: Toàn bộ suite test (hơn 370 tests) chạy thành công 100% thông qua Harness CLI wrapper.

---

## 3. Bản đồ Bead Công việc (Work Shape / Bead Map)

Sau khi được phê duyệt GATE 2, chúng ta sẽ khởi tạo các Beads sau:
* `br-201` [task]: SEE - Tái cấu trúc CSS hệ thống và Theme Switcher (`style.css`, `base.html`).
* `br-202` [task]: SEE - Cải tiến trang Tra cứu Hóa đơn và Bento Grid KPI (`invoices.html`).
* `br-203` [task]: SEE - Vẽ biểu đồ dòng tiền SVG chuyển sắc (`cashflow.html`).
* `br-204` [task]: SEE - Tối ưu hóa Form CRO Phát hành & Đăng nhập (`issue_invoice.html`, `login.html`).
* `br-205` [task]: RUN - Rà soát Captcha Solver, Archiver & Nâng cấp Pytest Suite.
