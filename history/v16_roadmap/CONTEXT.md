# Khuym Context: Version 16.0.0 Vietnamese E-Invoice Customs & Import-Export Duty Audit Hub, PIT & Social Insurance Audit Engine, and Secure E-Invoice Archiving & TSA Cryptographic Vault

Quyết định thiết kế và phạm vi nghiệp vụ cho việc triển khai Phiên bản 16.0.0.

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `v16_roadmap`
* **Quy mô (Scope)**: `Deep` (Lộ trình chiến lược kiểm toán thuế hải quan xuất nhập khẩu, kiểm tra tuân thủ bảng lương bảo hiểm TNCN, lưu trữ bảo mật 10 năm theo Nghị định 123 và xác thực chữ ký số dài hạn TSA).
* **Phân loại Phân hệ (Domain Types)**:
  - `SEE`: Giao diện Bảng kê thuế xuất nhập khẩu và hải quan, Panel đối chiếu tờ khai và hóa đơn nội địa, Dashboard kiểm toán bảng lương TNCN & BHXH, Wizard quyết toán TNCN (Mẫu 05/QTT-TNCN), Kho hồ sơ lưu trữ số Decree 123, Bảng phân tích chữ ký số và TSA.
  - `CALL`: Các API: `/api/customs/parse`, `/api/customs/reconcile`, `/api/pit/payroll-audit`, `/api/pit/finalize`, `/api/vault/archive`, `/api/vault/verify-signature`.
  - `RUN`: Trình phân tích tờ khai hải quan XML, công cụ đối chiếu hóa đơn nhập khẩu, máy tính BHXH và thuế TNCN progressive, công cụ đóng gói zip mã hóa AES-256, dịch vụ phân tích chữ ký số XML và TSA token.
  - `ORGANIZE`: Bảng dữ liệu `CustomsDeclaration`, `CustomsReconciliation`, `PayrollAuditRecord`, `InvoiceArchive`, `TSAVerificationLog`, schema SQLite mở rộng.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu Lộ trình v16]**: Triển khai giải pháp v16.0.0 bao gồm ba trụ cột chính: Kiểm toán thuế hải quan & xuất nhập khẩu (US-190, US-191) đối chiếu tờ khai VNACCS; Kiểm toán BHXH & Thuế TNCN (US-192, US-193) tự động lập tờ khai 05/QTT; Lưu trữ bảo mật & Xác thực chữ ký số dài hạn TSA (US-194, US-195) phục vụ thanh tra thuế sau nhiều năm.
* **D2 [Cú pháp Tờ khai Hải quan XML]**: Trình phân tích tờ khai hải quan (US-190) sẽ xử lý tệp tin XML chuẩn xuất ra từ các hệ thống khai hải quan VNACCS/ECUS, trích xuất mã số tờ khai, mã loại hình nhập khẩu (A11, A12, v.v.), trị giá tính thuế, thuế suất và tỷ giá tính thuế của hải quan.
* **D3 [Kiểm toán Bảo hiểm & Phụ cấp TNCN]**: Bộ kiểm toán bảng lương (US-192) sẽ áp dụng tỷ lệ đóng BHXH, BHYT, BHTN theo luật hiện hành tại Việt Nam (người lao động 10.5%, người sử dụng lao động 21.5%) dựa trên mức lương đóng bảo hiểm trần theo lương cơ sở vùng. Khống chế các khoản phụ cấp không chịu thuế (ăn trưa tối đa 730,000 VND/tháng, điện thoại/trang phục theo quy chế nội bộ nhưng không vượt ngưỡng hợp lý).
* **D4 [HTKK-Ready PIT XML]**: XML quyết toán thuế TNCN (US-193) được thiết kế và serialize theo định dạng XSD của Tổng cục Thuế Việt Nam dành cho mẫu 05/QTT-TNCN để người dùng có thể nhập trực tiếp vào phần mềm HTKK hoặc nộp qua cổng thuedientu.
* **D5 [Quy chuẩn Lưu trữ & TSA]**: Tệp tin hóa đơn sẽ được nén và mã hóa bằng AES-256 với khóa mã hóa riêng của từng tenant (US-194). Trình xác thực chữ ký (US-195) sẽ kiểm tra tính toàn vẹn của thẻ chữ ký số `<Signature>` trong XML và giải mã timestamp RFC-3161 từ TSA đi kèm để chứng minh thời điểm ký số độc lập với đồng hồ máy tính.

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  - `templates/customs_audit.html` (Quản lý tờ khai hải quan, đối chiếu hóa đơn VAT nhập khẩu)
  - `templates/payroll_audit.html` (Bảng lương bảo hiểm, phụ cấp và wizard quyết toán thuế TNCN)
  - `templates/digital_vault.html` (Kho lưu trữ hóa đơn điện tử mã hóa, tra cứu chỉ mục)
  - `static/js/customs.js` (Gọi API parser tờ khai, đối chiếu chênh lệch)
  - `static/js/payroll.js` (Audit bảng lương Excel, xuất tờ khai mẫu 05/QTT)
  - `static/js/vault.js` (Tìm kiếm chỉ mục, mã hóa tài liệu, xác thực chữ ký TSA)
* **Nghiệp vụ (RUN / CALL / ORGANIZE)**:
  - `invoices/models.py` (Khai báo `CustomsDeclaration`, `PayrollAuditRecord`, `InvoiceArchive`)
  - `invoices/customs_parser.py` (Trình phân tích XML tờ khai hải quan VNACCS)
  - `invoices/customs_matcher.py` (Logic đối chiếu tờ khai và hóa đơn)
  - `invoices/payroll_auditor.py` (Logic tính toán BHXH và phân tích phụ cấp miễn thuế)
  - `invoices/pit_finalizer.py` (Tổng hợp quyết toán TNCN, serialize XML mẫu 05/QTT)
  - `invoices/digital_vault.py` (Đóng gói nén mã hóa AES, cơ chế index metadata)
  - `invoices/signature_validator.py` (Xác thực chữ ký số XML, kiểm tra OCSP/CRL và TSA)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)

* Kết nối trực tiếp API với hệ thống thông quan của Tổng cục Hải quan. (Hoãn lại do hải quan chưa mở cổng API công cộng, chỉ hỗ trợ import tệp XML tờ khai thủ công).
* Quản lý đóng bảo hiểm xã hội điện tử (cắm USB Token để kê khai bảo hiểm trực tiếp). (Hoãn lại, chỉ tập trung vào kiểm toán số liệu và phát hiện rủi ro thuế).
* Lưu trữ phân tán IPFS cho hóa đơn. (Hoãn lại, sử dụng ZIP mã hóa cục bộ kết hợp backup S3/Cloud Storage để đảm bảo tốc độ truy cập cao nhất).
