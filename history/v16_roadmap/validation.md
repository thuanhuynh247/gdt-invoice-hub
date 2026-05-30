# Feasibility Validation: Version 16.0.0 Vietnamese E-Invoice Customs & Import-Export Duty Audit Hub, PIT & Social Insurance Audit Engine, and Secure E-Invoice Archiving & TSA Cryptographic Vault

Báo cáo kết quả kiểm chứng tính khả thi kỹ thuật và ma trận sẵn sàng triển khai cho Version 16.0.0.

---

## 1. Ma trận Khả thi (Feasibility Matrix)

| Phân hệ / Tính năng | Tính khả thi | Phương án chứng minh | Mức độ rủi ro | Trạng thái sẵn sàng |
|---|---|---|---|---|
| **Customs XML Parser** | **95%** | Sử dụng `xml.etree.ElementTree` hoặc `lxml` để phân tích cấu trúc XML tờ khai của VNACCS/ECUS. | Thấp | **READY** |
| **Customs-to-Invoice Matcher** | **100%** | Đối chiếu thông tin số tờ khai hải quan trên các hóa đơn đầu vào (phần ghi chú hoặc mã sản phẩm) để liên kết tự động. | Thấp | **READY** |
| **Payroll Compliance Engine** | **90%** | Dùng thư viện `openpyxl` để đọc dữ liệu bảng lương dạng lưới Excel, áp dụng luật bảo hiểm xã hội và thuế suất lũy tiến từng phần. | Thấp | **READY** |
| **PIT Finalizer & Form 05** | **90%** | Tạo XML theo chuẩn XSD mẫu 05/QTT-TNCN của Tổng cục Thuế bằng ElementTree, đảm bảo nạp được vào HTKK. | Trung bình | **READY** |
| **Decree 123 Digital Vault** | **95%** | Sử dụng thư viện `zipfile` và `cryptography.fernet` (hoặc `pycryptodome` AES) để đóng gói mã hóa hóa đơn, đánh chỉ mục tìm kiếm trên SQLite. | Thấp | **READY** |
| **TSA Signature Validator** | **90%** | Trích xuất chữ ký số XML sử dụng thư viện `signxml` hoặc xử lý thủ công thẻ XML dsig, giải mã timestamp token dùng `pyasn1` / `asn1crypto`. | Trung bình | **READY** |

---

## 2. Kế hoạch Kiểm thử & Hậu nghiệm (Verification Strategy)

1. **Kiểm thử Customs XML Parser (`tests/test_v16_customs_parser.py`)**:
   - Giả lập tệp XML tờ khai hải quan nhập khẩu hàng tiêu dùng.
   - Xác minh trích xuất đúng mã loại hình, trị giá tính thuế, số tiền thuế nhập khẩu và thuế GTGT hàng nhập khẩu.
   - Xác minh tính đúng đắn của việc quy đổi trị giá ngoại tệ sang VND theo tỷ giá tờ khai.

2. **Kiểm thử Customs-to-Invoice Matcher (`tests/test_v16_customs_matcher.py`)**:
   - Tạo hóa đơn GTGT đầu vào liên quan đến hàng nhập khẩu.
   - Khởi chạy thuật toán đối chiếu và kiểm tra xem có phát hiện chênh lệch thuế GTGT đầu vào hải quan so với hóa đơn thực tế hay không.

3. **Kiểm thử Payroll Compliance Engine (`tests/test_v16_payroll_auditor.py`)**:
   - Nạp bảng lương Excel chứa các lỗi tính sai BHXH hoặc phụ cấp trang phục vượt mức 5,000,000 VND/năm.
   - Xác minh công cụ phát hiện và cảnh báo chính xác nhân viên bị tính sai số tiền và các khoản phụ cấp bị tính thuế bổ sung.

4. **Kiểm thử PIT Finalizer & Form 05 (`tests/test_v16_pit_finalizer.py`)**:
   - Chạy quyết toán thuế TNCN năm cho danh sách 50 nhân viên với thu nhập lũy tiến và giảm trừ gia cảnh khác nhau.
   - Xác minh file XML sinh ra có cấu trúc chính xác các thẻ và khớp số tiền thuế quyết toán cuối cùng.

5. **Kiểm thử Decree 123 Digital Vault (`tests/test_v16_digital_vault.py`)**:
   - Chạy quy trình đóng gói lưu trữ cho 100 hóa đơn nháp.
   - Kiểm tra xem tệp tin ZIP lưu trên đĩa có thực sự được mã hóa AES hay không (đọc thô không giải mã được).
   - Truy vấn tìm kiếm hóa đơn theo từ khóa sản phẩm trong cơ sở dữ liệu chỉ mục và kiểm tra tốc độ trả kết quả (<100ms).

6. **Kiểm thử TSA Signature Validator (`tests/test_v16_signature_validator.py`)**:
   - Tải tệp XML hóa đơn gốc có chữ ký số hợp lệ và một tệp bị sửa đổi giá trị tiền.
   - Xác minh bộ validator phát hiện tệp bị tampered và báo lỗi chữ ký số không khớp.
   - Xác minh giải mã thành công TSA timestamp chứng minh thời điểm ký.
