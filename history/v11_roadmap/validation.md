# Feasibility Validation: Version 11.0.0 Enterprise Security Audit Ledger, GDT Portal Sync Resiliency & Tax Risk Analytics

Báo cáo kết quả kiểm chứng tính khả thi kỹ thuật, dữ liệu thực nghiệm và ma trận sẵn sàng triển khai cho Version 11.0.0.

---

## 1. Ma trận Khả thi (Feasibility Matrix)

| Phân hệ / Tính năng | Tính khả thi | Phương án chứng minh | Mức độ rủi ro | Trạng thái sẵn sàng |
|---|---|---|---|---|
| **Immutable Security Audit Log** | **100%** | Khai báo bảng `SecurityAuditLog` và sử dụng SQLAlchemy event listener để chặn các câu lệnh UPDATE/DELETE trực tiếp. | Thấp | **READY** |
| **Resilient Sync Queue** | **100%** | Tận dụng Python `ThreadPoolExecutor` chạy nền trong scheduler thread, gom các task đồng bộ độc lập cho từng MST. | Thấp | **READY** |
| **Solver Health Monitor** | **100%** | Tạo bộ đếm in-memory hoặc lưu SQLite các lượt giải thành công/thất bại của solver ddddocr. | Thấp | **READY** |
| **Tax Risk Scoreboard** | **100%** | Tích hợp thêm các bộ đếm thống kê warning trên tập hóa đơn và vẽ biểu đồ hình cột/tròn qua SVG động. | Thấp | **READY** |
| **Signed Compliance Report** | **100%** | Băm dữ liệu ledger hóa đơn bằng SHA-256 và sinh file PDF/Excel kèm chuỗi hash kiểm tra tính toàn vẹn. | Thấp | **READY** |

---

## 2. Kế hoạch Kiểm thử & Hậu nghiệm (Verification Strategy)

Khi bước vào giai đoạn thực thi (Execution), chúng tôi sẽ triển khai các bộ test tự động sau:
1. **Kiểm thử Security Audit Log (`tests/test_v11_audit_log.py`)**:
   - Xác minh ghi log thành công sau khi đăng nhập, chuyển đổi MST, thực hiện repair.
   - Xác minh các lệnh sửa/xóa log trực tiếp bị chặn hoặc ném ngoại lệ.
2. **Kiểm thử Resilient Sync (`tests/test_v11_sync_resiliency.py`)**:
   - Giả lập crawler chạy song song cho 3 MST khác nhau.
   - Xác minh nếu 1 MST bị lỗi captcha hoặc timeout, 2 MST còn lại vẫn tiếp tục crawl và lưu hóa đơn thành công.
3. **Kiểm thử Solver Health API (`tests/test_v11_solver_health.py`)**:
   - Gửi yêu cầu giải captcha giả lập thành công/thất bại và truy vấn `/api/sync/health` để kiểm tra tỉ lệ chính xác.
4. **Kiểm thử Signed Report (`tests/test_v11_signed_report.py`)**:
   - Xuất báo cáo `/api/reports/signed-compliance`.
   - Đọc lại file PDF/Excel và xác minh tính toàn vẹn của chuỗi băm SHA-256 đi kèm.
