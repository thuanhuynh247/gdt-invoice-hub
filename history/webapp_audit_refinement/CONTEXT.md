# Khuym Context: Webapp UI/UX Audit and Logic Refinement

Quyết định thiết kế và phạm vi nghiệp vụ cho việc rà soát thẩm mỹ (UI/UX) và tuân thủ nghiệp vụ (Logic Audit) cho hệ thống GDT Invoice Hub.

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `webapp_audit_refinement`
* **Quy mô (Scope)**: `Deep` (Ảnh hưởng toàn bộ giao diện và các bộ phận nghiệp vụ của hệ thống).
* **Phân loại Phân hệ (Domain Types)**:
  * `SEE`: Cải tiến giao diện người dùng (như invoices, cashflow, issue_invoice, login).
  * `RUN`: Rà soát các bộ xử lý chạy ngầm, luồng đồng bộ, captcha solver và an ninh bảo mật.
  * `ORGANIZE`: Cấu trúc lưu trữ hỗn hợp SQLite + Zip cold partition, kiểm tra tính hợp lệ của mã số thuế doanh nghiệp.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu kép]**: Thực hiện audit và tối ưu hóa song song cả tính thẩm mỹ giao diện người dùng (UI/UX) và tính chính xác, an toàn của logic nghiệp vụ & bảo mật.
* **D2 [Thẩm mỹ Glassmorphism & Sleek Dark/Light Mode]**: Cải tiến giao diện đồng nhất cho tất cả các trang chính sử dụng thiết kế kính mờ tinh tế (Vibrant Glassmorphism), bo góc mịn, bóng đổ mượt, và tối ưu hóa bộ lọc cùng bảng dữ liệu có độ phản hồi cao trên di động (Mobile responsive tables). Tích hợp nút chuyển đổi Dark/Light mode liền mạch.
* **D3 [Nâng cấp Toàn diện Bộ Test tự động]**: Rà soát kỹ lượng toàn bộ hệ thống logic và củng cố chất lượng thông qua việc nâng cấp bộ công cụ kiểm thử tự động (Pytest suite) đạt độ phủ tối đa, chạy thông qua công cụ điều phối Harness CLI.

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  * `templates/base.html` (Khung trang chung, CSS Fonts, Navigation & Theme Switcher)
  * `templates/invoices.html` (Trang tra cứu & Bento Grid hiển thị hóa đơn)
  * `templates/cashflow.html` (Trang trực quan hóa dự báo dòng tiền bằng biểu đồ động)
  * `templates/issue_invoice.html` (Form phát hành hóa đơn với Form CRO)
  * `static/css/style.css` (Tệp style chính chứa định nghĩa CSS biến môi trường màu và hiệu ứng)
* **Nghiệp vụ (RUN / ORGANIZE)**:
  * `app.py` (Cấu hình Flask, Middleware bảo mật, Migration tự động)
  * `invoices/archiver.py` (Lưu trữ nén lạnh dữ liệu lịch sử)
  * `invoices/event_streamer.py` & `invoices/routes.py` (Hệ thống Webhook và API xử lý)
  * `auth/captcha_solver.py` (Bộ giải mã Captcha tự động)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)
* Tích hợp dịch vụ OCR phân tích hình ảnh hóa đơn từ camera điện thoại (Sẽ làm trong Phase tiếp theo).
* Chuyển đổi toàn bộ giao diện từ Bootstrap sang Tailwind CSS v4 (Hoãn lại để giữ độ nhẹ và ổn định của mã nguồn hiện tại).
