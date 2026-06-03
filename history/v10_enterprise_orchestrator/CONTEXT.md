# Khuym Context: Version 10.0.0 Enterprise Tax Advisory RAG Pro & Multi-Tenancy Orchestrator

Quyết định thiết kế và phạm vi nghiệp vụ cho việc triển khai Phiên bản 10.0.0 (Enterprise Tax Advisory RAG Pro, Smart Auto-Correction, Fraud Fingerprinting & Multi-Tenancy Router).

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `v10_enterprise_orchestrator`
* **Quy mô (Scope)**: `Deep` (Lộ trình phát triển lớn bao trùm nhiều phân hệ cốt lõi).
* **Phân loại Phân hệ (Domain Types)**:
  * `SEE`: Tích hợp Bảng tư vấn Thuế AI (AI Tax Advisory Panel) phong cách Glassmorphism và giao diện Giám sát Multi-tenant chuyên sâu.
  * `CALL`: Xây dựng các API RAG mới `/api/ai/advise`, `/api/fraud/fingerprint` và bộ định tuyến Tenant API Router.
  * `RUN`: Tiến trình chạy ngầm lập chỉ mục Vector văn bản Luật Thuế 48 & 149 nâng cao, quét fingerprint gian lận thuế thời gian thực.
  * `ORGANIZE`: Cơ chế Multi-tenant SQLite Router định tuyến kết nối động dựa trên profile doanh nghiệp và lưu trữ vector store cục bộ.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu Lộ trình v10]**: Triển khai gói giải pháp Doanh nghiệp v10.0.0 tích hợp ba trụ cột: AI RAG Chuyên sâu Luật Thuế Việt Nam, Tự động phát hiện & sửa sai thông tin hóa đơn (Smart Auto-Correction), và Công cụ định tuyến cơ sở dữ liệu đa khách thuê bảo mật tuyệt đối (Multi-Tenancy Dynamic Routing).
* **D2 [Offline RAG & FAISS/SQLite Vector]**: Hệ thống AI RAG sẽ hoạt động hoàn toàn cục bộ (Fully Offline/Local) sử dụng Ollama (Gemma-4/Llama-3) và cơ chế lưu trữ Vector file tĩnh FAISS/SQLite để bảo mật dữ liệu tối đa và tối ưu hóa chi phí API.
* **D3 [Interactive Auto-Correction Suggestions]**: Áp dụng cơ chế tạo đề xuất sửa đổi dưới dạng nháp (Draft Suggestion) và chờ kế toán phê duyệt thủ công (Single-Click Approval) trước khi ghi đè vào DB, bảo toàn tính kiểm soát của kiểm toán viên.
* **D4 [Hard Blocking Fraud Fingerprints]**: Công cụ kiểm tra gian lận sẽ thực hiện kiểm tra chặn cứng (Hard Blocking) ngay khi import. Bất kỳ hóa đơn nào trùng dấu vết gian lận hoặc MST đen sẽ bị từ chối nhập để bảo vệ sự trong sạch của cơ sở dữ liệu.

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  * `templates/base.html` (Thêm menu Trợ lý RAG Pro & Quản lý Multi-tenant)
  * `templates/invoices.html` (Tích hợp widget cảnh báo gian lận và đề xuất sửa đổi)
  * `static/js/main.js` (Gọi API RAG, hiển thị hộp thoại chat thông minh)
* **Nghiệp vụ (RUN / CALL / ORGANIZE)**:
  * `invoices/ai_service.py` (Mở rộng RAG vector search, Law 48/149 parsing)
  * `invoices/models.py` & `invoices/routes.py` (Multi-tenant dynamic engine router, database isolation layers)
  * `auth/security.py` (Fingerprint fraud engine check)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)

* Tích hợp Blockchain công khai (Hoãn lại, sử dụng Cryptographic Hash Ledger nội bộ để đảm bảo tốc độ và chi phí).
* Hỗ trợ đa ngôn ngữ Anh/Trung cho chatbot RAG (Hoãn lại, ưu tiên độ chính xác tiếng Việt tối đa cho các luật thuế Việt Nam).
