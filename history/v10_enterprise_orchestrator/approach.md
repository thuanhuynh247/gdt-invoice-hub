# Khuym Approach: Version 10.0.0 Enterprise Tax Advisory RAG Pro & Multi-Tenancy Orchestrator

Định hướng giải pháp kỹ thuật, phân tích rủi ro, kế hoạch giảm thiểu rủi ro và các kịch bản kiểm chứng tính khả thi kỹ thuật.

---

## 1. Phương án Kỹ thuật (Technical Path)

### Phân hệ A: Bộ định tuyến Dynamic Multi-Tenancy SQL Router
* **Mục tiêu**: Định tuyến động tất cả các truy vấn SQLAlchemy tới file SQLite biệt lập `data/tenant_<mst>.db` dựa trên `session["tax_code"]` của tài khoản đang đăng nhập, thay vì dùng chung tệp CSDL mặc định.
* **Giải pháp**:
  1. Triển khai lớp `TenantDatabaseRouter` trong `invoices/multitenant_service.py` kế thừa từ `sqlalchemy.engine.Engine` hoặc tùy biến `Flask-SQLAlchemy` bind mapper.
  2. Bổ sung hàm định tuyến kết nối động: `db.session.bind` hoặc sử dụng `SQLAlchemy(binds=...)` để định tuyến theo luồng yêu cầu (Request context).
  3. Tự động gọi `bootstrap_tenant_db(mst)` khi định tuyến tới một tenant chưa khởi tạo CSDL riêng.
  4. Đảm bảo toàn bộ 373 kiểm thử cũ vẫn chạy thành công trên CSDL gốc (Default fallback) khi không có session hoạt động.

### Phân hệ B: Trợ lý AI RAG Pro luật thuế ngoại tuyến (Local Ollama + FTS5 Vector)
* **Mục tiêu**: Xây dựng kênh chat tư vấn thuế chuyên sâu cho doanh nghiệp tích hợp trong giao diện.
* **Giải pháp**:
  1. Mở rộng `invoices/ai_service.py` với API `/api/ai/advise` hỗ trợ lưu lịch sử hội thoại.
  2. Thiết lập cơ chế gom cụm ngữ cảnh kết hợp (Hybrid Search): Truy xuất từ khóa chính xác FTS5 trên các văn bản Luật Thuế 48 & 149 cùng các thông tư liên quan kết hợp với bộ lọc Metadata theo MST của Tenant.
  3. Sử dụng mô hình cục bộ Gemma-4/Llama-3 qua Ollama API cục bộ (`http://localhost:11434`), tích hợp câu hỏi lịch sử để tạo hội thoại liên tục (Conversational memory).

### Phân hệ C: Cổng đề xuất sửa lỗi thông minh (Smart Auto-Correction Proposal)
* **Mục tiêu**: AI tự động phát hiện lỗi lệch thông tin và đề xuất sửa đổi dưới dạng Nháp thay vì tự động ghi đè, trao quyền kiểm soát cho kế toán.
* **Giải pháp**:
  1. Tạo bảng CSDL mới `invoice_correction_proposal` (id, invoice_id, field_name, original_value, proposed_value, explanation, status: pending/approved/rejected, created_at).
  2. Khi chạy `AIComplianceAuditor`, nếu phát hiện sai lệch (như tên nhà cung cấp không khớp MST, số học không khớp thuế suất), tạo bản ghi `pending` tương ứng.
  3. Viết API `/api/corrections/pending` để lấy danh sách đề xuất và `/api/corrections/<id>/approve` (hoặc `reject`) để xử lý. Khi phê duyệt, hệ thống sẽ sửa trực tiếp trường tương ứng trong bảng `invoice` và đóng đề xuất.
  4. Thiết kế Glassmorphism Widget hiển thị danh sách đề xuất ngay trên đầu trang tra cứu hóa đơn.

### Phân hệ D: Chặn cứng gian lận hóa đơn đầu vào (Fraud Fingerprinting Hard Blocker)
* **Mục tiêu**: Quét dấu hiệu gian lận (trùng lặp Hash chữ ký, nhà cung cấp nằm trong danh sách đen GDT, chuỗi giao dịch tuần hoàn giả lập) và chặn đứng ở cổng import.
* **Giải pháp**:
  1. Nâng cấp hàm `import_invoice` trong `invoices/service.py` và `invoices/parser.py`.
  2. Kiểm tra chéo chữ ký số của hóa đơn với cơ sở dữ liệu lịch sử để phát hiện trùng lặp Hash gian lận.
  3. So khớp MST người bán với danh mục đen của Tổng cục Thuế (`partner.mst_status == 'blacklist'`).
  4. Nếu rủi ro cao, ném ngoại lệ `FraudValidationError` và trả về mã lỗi HTTP `400 Bad Request` kèm theo báo cáo lý do chặn chi tiết trên UI.

---

## 2. Phân tích Rủi ro & Kiểm chứng (Risks & Spike Probes)

* **Rủi ro 1: Rò rỉ kết nối & Xung đột luồng (Thread-safety) khi định tuyến động**
  * *Hệ quả*: Lỗi khóa DB SQLite (`database is locked`), rò rỉ session giữa các MST khác nhau trong môi trường đa luồng (multi-threaded Flask dev server).
  * *Kế hoạch kiểm chứng (Spike Probe)*: Viết một đoạn mã chạy thử `tests/test_multitenant_routing_spike.py` tạo 10 luồng song song gửi yêu cầu định dạng khác nhau để xác nhận các kết nối độc lập hoàn toàn và giải phóng kết nối sau request.
* **Rủi ro 2: Thời gian phản hồi của mô hình LLM cục bộ Ollama quá lâu gây Timeout**
  * *Hệ quả*: Giao diện web bị đơ, Flask worker bị ngắt kết nối.
  * *Kế hoạch kiểm chứng*: Thiết lập SSE (Server-Sent Events) hoặc xử lý phản hồi dạng Streaming trong API chat `/api/ai/advise` để người dùng nhìn thấy AI gõ chữ thời gian thực thay vì chờ đợi lâu.

---

## 3. Các Tệp Tin Ảnh Hưởng (Affected Files)

* **Multi-Tenancy**:
  * `invoices/multitenant_service.py` (Mở rộng router kết nối và quản lý vòng đời session).
  * `extensions.py` / `app.py` (Tích hợp middleware dynamic routing).
* **AI RAG Pro**:
  * `invoices/ai_service.py` (API Chat, prompt nâng cao và truy xuất vector/FTS5).
  * `templates/base.html` & `static/js/main.js` (Thêm bảng Chat trợ lý Glassmorphism nổi trên góc phải).
* **Auto-Correction**:
  * `invoices/models.py` (Định nghĩa bảng `InvoiceCorrectionProposal`).
  * `invoices/routes.py` (Thêm API duyệt/từ chối sửa đổi).
  * `templates/invoices.html` (Widget hiển thị đề xuất sửa đổi và nút phê duyệt nhanh).
* **Fraud Fingerprinting**:
  * `invoices/parser.py` (Bổ sung validate dấu vết gian lận & chặn cứng).

---

## 4. Các Câu hỏi Kiểm chứng (Validating Questions)
1. Các CSDL tenant SQLite riêng lẻ sẽ dùng chung định nghĩa schema từ `invoices/models.py` hay cần cô lập và lược bỏ các bảng hệ thống chung (như `system_config`, `scheduler_log`) để giảm dung lượng file?
2. Có cần giới hạn số lượng đề xuất sửa đổi tối đa hiển thị trên giao diện của mỗi hóa đơn để tránh spam dữ liệu không?
