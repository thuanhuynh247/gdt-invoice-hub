# Khuym Context: Version 15.0.0 Automated Corporate Income Tax (CIT) Finalization, Visual Scenario Modeler & Intelligent XML Schema Expansion

Quyết định thiết kế và phạm vi nghiệp vụ cho việc triển khai Phiên bản 15.0.0.

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `v15_roadmap`
* **Quy mô (Scope)**: `Deep` (Lộ trình chiến lược tự động hóa quyết toán thuế TNDN, công cụ mô phỏng tình huống tài chính và mở rộng schema XML lưu trữ metadata động cùng sổ cái kiểm toán blockchain).
* **Phân loại Phân hệ (Domain Types)**:
  - `SEE`: Giao diện Quyết toán thuế TNDN (Mẫu 03/TNDN), Bảng điều khiển mô phỏng tình huống (Slider controls), Panel cấu hình Schema mở rộng, Bảng kiểm tra xác thực Sổ cái Blockchain.
  - `CALL`: Các API: `/api/cit/finalize`, `/api/cit/simulate-scenario`, `/api/schema/extensions`, `/api/schema/reports`, `/api/approval/workflows`, `/api/blockchain/verify`.
  - `RUN`: Công cụ tổng hợp dữ liệu CIT, máy tính mô phỏng what-if tài chính, trình phân tích cú pháp XML mở rộng động, dịch vụ kiểm tra chữ ký đa cấp, công cụ tạo khối sổ cái blockchain mock.
  - `ORGANIZE`: Bảng dữ liệu `CITScenario`, `SchemaExtension`, `ApprovalWorkflow`, `ApprovalSignature`, `IntegrityLedger`, schema SQLite mở rộng.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu Lộ trình v15]**: Triển khai giải pháp v15.0.0 bao gồm ba trụ cột chính: Quyết toán thuế TNDN tự động (US-180, US-181) tổng hợp Form 03/TNDN và mô phỏng stress-test; Schema mở rộng XML (US-182, US-183) lưu trữ dữ liệu ngành đặc thù vào trường JSON; Cryptographic Trust (US-184, US-185) tích hợp ký số đa cấp phê duyệt nội bộ và lưu vết SHA-256 sổ cái bảo mật.
* **D2 [Logic Quyết toán TNDN & Khống chế lãi vay]**: Logic CIT (US-180) sẽ tự động liên kết với tính toán giao dịch liên kết v14, loại trừ chi phí lãi vay vượt mức 30% EBITDA theo Nghị định 132/2020/NĐ-CP và các khoản chi phí không hợp lệ khác trước khi áp thuế suất CIT hiện hành (mặc định 20%).
* **D3 [Lược đồ XML động - E-Invoice Metadata]**: Lược đồ mở rộng (US-182) không thay đổi cấu trúc bảng SQL tĩnh mà lưu trữ các thẻ định nghĩa động (XML Path -> JSON Key) vào cột `metadata_json` kiểu TEXT/JSON để giữ tính tương thích cao và hiệu suất tối đa.
* **D4 [Xác thực Sổ cái Blockchain mock]**: Sổ cái Blockchain (US-185) xây dựng dưới dạng một bảng liên kết tuần tự (hash chain) trong SQLite. Khối sau chứa hash khối trước. Nếu có bất kỳ sự thay đổi trực tiếp nào trên bảng Invoice mà không thông qua workflow, hash chain sẽ đứt gãy, lập tức báo động tại Dashboard kiểm toán.
* **D5 [Quy trình Phê duyệt Đa chữ ký]**: Trước khi gửi ký số phát hành lên cổng thuế, hóa đơn phải được phê duyệt tuần tự qua các cấp bậc kế toán viên -> kế toán trưởng -> giám đốc. Mỗi bước ghi nhận dấu vân tay mã hóa chữ ký (signature hash).

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  - `templates/cit_finalization.html` (Bảng quyết toán thuế TNDN, form 03/TNDN, slider simulation)
  - `templates/schema_builder.html` (Giao diện tạo tag XML động và tra cứu báo cáo ngành)
  - `templates/approval_ledger.html` (Quản lý workflow phê duyệt và xác thực sổ cái)
  - `static/js/cit_final.js` (Gọi API CIT, mô phỏng tham số, xuất tờ khai)
  - `static/js/schema_ext.js` (Cấu hình trường động, bộ lọc thông minh)
  - `static/js/blockchain_audit.js` (Workflow ký phê duyệt, tải XML đối chiếu SHA-256)
* **Nghiệp vụ (RUN / CALL / ORGANIZE)**:
  - `invoices/models.py` (Khai báo `CITScenario`, `SchemaExtension`, `ApprovalWorkflow`, `IntegrityLedger`)
  - `invoices/cit_engine.py` (Tổng hợp CIT, tạo XML Form 03/TNDN HTKK)
  - `invoices/cit_modeler.py` (Tác vụ toán học mô phỏng kịch bản dòng tiền và thuế)
  - `invoices/schema_extensions.py` (Parser XML động, trích xuất metadata JSON, query builder)
  - `invoices/integrity_ledger.py` (Xây dựng Hash Chain, xác thực tính toàn vẹn XML)
  - `auth/approval_workflow.py` (Quản lý trạng thái và chữ ký duyệt đa cấp)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)

* Tích hợp với hợp đồng thông minh trên mạng Ethereum/Hyperledger thực tế. (Hoãn lại, sử dụng thuật toán hash-chain lưu SQLite để tối ưu hóa chi phí và tốc độ).
* Tự động đồng bộ tờ khai 03/TNDN trực tiếp lên hệ thống Etax của Tổng cục Thuế. (Hoãn lại, chỉ hỗ trợ xuất file XML để người dùng nộp thủ công qua HTKK).
