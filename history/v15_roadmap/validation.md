# Feasibility Validation: Version 15.0.0 Automated Corporate Income Tax (CIT) Finalization, Visual Scenario Modeler & Intelligent XML Schema Expansion

Báo cáo kết quả kiểm chứng tính khả thi kỹ thuật và ma trận sẵn sàng triển khai cho Version 15.0.0.

---

## 1. Ma trận Khả thi (Feasibility Matrix)

| Phân hệ / Tính năng | Tính khả thi | Phương án chứng minh | Mức độ rủi ro | Trạng thái sẵn sàng |
|---|---|---|---|---|
| **CIT Calculation & Scaffolder** | **95%** | Tổng hợp từ bảng doanh thu và chi phí hợp lệ/không hợp lệ. Sinh tệp tin XML chuẩn HTKK thông qua thư viện `xml.etree.ElementTree` hoặc `lxml`. | Thấp | **READY** |
| **CIT Scenario Modeler** | **100%** | Xây dựng công cụ toán học tính toán tuyến tính CIT dựa trên tham số người dùng nhập từ slider. Lưu trữ các kịch bản vào tệp JSON. | Thấp | **READY** |
| **Schema Extension Engine** | **95%** | Trích xuất các thẻ XML động sử dụng XPath (`def/xml_path`) và lưu thành chuỗi JSON trong cột `metadata_json` kiểu TEXT của SQLite. | Thấp | **READY** |
| **Dynamic Metadata Filter** | **100%** | Sử dụng hàm `json_extract` của SQLite trong câu lệnh SELECT để truy vấn trực tiếp vào dữ liệu động mà không cần thay đổi schema bảng. | Thấp | **READY** |
| **Multi-Signature Approvals** | **100%** | Thiết lập bảng trạng thái quy trình phê duyệt (`ApprovalWorkflow`) liên kết với người dùng và hóa đơn nháp, kiểm tra trước khi ký số. | Thấp | **READY** |
| **Blockchain Audit Ledger** | **90%** | Xây dựng chuỗi liên kết băm (hash chain) bằng thuật toán SHA-256. Khối mới chứa hash khối cũ để phát hiện sửa đổi trực tiếp vào database. | Trung bình | **READY** |

---

## 2. Kế hoạch Kiểm thử & Hậu nghiệm (Verification Strategy)

1. **Kiểm thử CIT Calculation & Scaffolder (`tests/test_v15_cit_engine.py`)**:
   - Giả lập doanh thu và các chi phí hợp lý. Ghi nhận chi phí không hợp lệ thủ công và chi phí lãi vay liên kết.
   - Xác minh thuật toán tính CIT khấu trừ đúng 30% EBITDA lãi vay và áp thuế suất CIT chính xác.
   - Xác minh cấu trúc XML Form 03/TNDN sinh ra đúng định dạng XML Schema của Tổng cục Thuế.

2. **Kiểm thử CIT Scenario Modeler (`tests/test_v15_cit_modeler.py`)**:
   - Gửi các tham số mô phỏng khác nhau (tăng doanh thu R&D, tăng lương, giảm chi phí).
   - Xác minh kết quả trả về khớp chính xác với công thức tài chính dự báo CIT.
   - Kiểm tra chức năng lưu và so sánh hai kịch bản.

3. **Kiểm thử Schema Extension Engine (`tests/test_v15_schema_extensions.py`)**:
   - Tạo cấu hình mở rộng trường dữ liệu (ví dụ: tag `ProjectID` trích xuất từ `/HDon/DSCVDVC/ProjectID`).
   - Upload hóa đơn XML chứa thẻ đó.
   - Xác minh giá trị trích xuất được lưu chính xác trong trường `metadata_json` dạng JSON.

4. **Kiểm thử Dynamic Metadata Filter (`tests/test_v15_metadata_reporter.py`)**:
   - Chạy truy vấn tìm kiếm hóa đơn theo trường động `ProjectID = 'PRJ-2026'`.
   - Xác minh SQLite thực thi truy vấn đúng và trả về danh sách hóa đơn tương ứng.
   - Kiểm tra xuất file Excel chứa cột trường mở rộng này.

5. **Kiểm thử Multi-Signature Approvals (`tests/test_v15_approval_workflow.py`)**:
   - Khởi tạo quy trình duyệt 3 cấp.
   - Thử nghiệm ký số hóa đơn khi chưa đủ cấp phê duyệt và xác minh hệ thống chặn phát hành.
   - Duyệt đủ các cấp và xác minh hệ thống cho phép ký số thành công.

6. **Kiểm thử Blockchain Audit Ledger (`tests/test_v15_integrity_ledger.py`)**:
   - Tạo các khối hóa đơn trong sổ cái hash chain.
   - Thử sửa đổi trực tiếp số tiền của một hóa đơn trong DB không thông qua API.
   - Gọi hàm kiểm tra và xác minh hệ thống phát hiện đứt gãy hash chain, báo động đỏ.
