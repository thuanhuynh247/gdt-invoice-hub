# Khuym Context: Version 11.0.0 Enterprise Security Audit Ledger, GDT Portal Sync Resiliency & Tax Risk Analytics

Quyết định thiết kế và phạm vi nghiệp vụ cho việc triển khai Phiên bản 11.0.0.

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `v11_roadmap`
* **Quy mô (Scope)**: `Deep` (Lộ trình phát triển lớn nâng cao khả năng vận hành bảo mật, hiệu năng crawler và phân tích rủi ro trực quan).
* **Phân loại Phân hệ (Domain Types)**:
  - `SEE`: Giao diện Audit Trail Viewer, Trực quan hóa Solver CAPTCHA Health, Dashboard Bảng điểm rủi ro Thuế (Tax Risk Scoreboard).
  - `CALL`: Các API: `/api/audit/logs`, `/api/sync/health`, `/api/reports/signed-compliance`.
  - `RUN`: Scheduler chạy ngầm đồng bộ song song nhiều MST, tiến trình ghi nhận và tổng hợp chỉ số giải mã CAPTCHA.
  - `ORGANIZE`: Bảng dữ liệu `SecurityAuditLog`, định dạng cấu trúc báo cáo ký số SHA-256 PDF/Excel.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu Lộ trình v11]**: Triển khai gói giải pháp Doanh nghiệp v11.0.0 tích hợp ba trụ cột: Nhật ký kiểm toán bảo mật đa khách thuê (Enterprise Security Audit Ledger), Bộ lập lịch crawl và theo dõi sức khỏe solver (Sync Resiliency Queue & Dashboard), và Bảng phân tích rủi ro Thuế kết hợp xuất báo cáo ký số SHA-256 (Tax Risk Scoreboard & Signed Exporter).
* **D2 [Log tính toàn vẹn và bất biến]**: Bản ghi trong bảng `SecurityAuditLog` chỉ hỗ trợ thao tác ghi (Append-Only), không hỗ trợ cập nhật hoặc xóa từ phía người dùng UI hoặc API thông thường để đảm bảo tính pháp lý và an toàn bảo mật.
* **D3 [Cô lập lỗi Crawler]**: Cơ chế đồng bộ đa MST sẽ sử dụng queue an toàn. Một lỗi đăng nhập hoặc sai captcha của MST này không được làm gián đoạn tiến trình crawl của MST khác.
* **D4 [Trực quan hóa Zero-Dependency]**: Tất cả biểu đồ phân bổ rủi ro và hiệu năng solver sẽ sử dụng SVG kết hợp HSL CSS Variables để tối ưu hóa hiệu năng tải trang và tránh xung đột với các framework giao diện.

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  - `templates/base.html` (Thêm menu Nhật ký kiểm toán & Giám sát crawler)
  - `templates/invoices.html` (Tích hợp tab/view cho Tax Risk Scoreboard)
  - `static/js/main.js` (Gọi API logs, API sync health, điều khiển render charts SVG)
* **Nghiệp vụ (RUN / CALL / ORGANIZE)**:
  - `invoices/models.py` (Khai báo class `SecurityAuditLog`)
  - `invoices/routes.py` (Khai báo API endpoints, xuất file báo cáo)
  - `invoices/scheduler.py` (Tích hợp queue chạy nền song song đa MST)
  - `invoices/service.py` (Thống kê solver captcha và tính toán rủi ro)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)

* Đồng bộ trực tiếp log bảo mật lên SIEM bên ngoài (Splunk/Elasticsearch). (Hoãn lại, lưu SQLite cục bộ để giảm tải hạ tầng).
* Tích hợp chữ ký số HSM phần cứng cho file PDF. (Hoãn lại, sử dụng băm SHA-256 kèm mã khóa ký đối xứng trong SystemConfig để xác minh tính toàn vẹn).
