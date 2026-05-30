# 📋 Kế Hoạch Triển Khai Next-Gen Webapp XML (Next-Gen Roadmap Execution Plan)

Kế hoạch này theo sát tài liệu **Next-Gen Roadmap** và cấu trúc lộ trình phát triển nâng cao cho ứng dụng **Invoice Download Webapp**. Dưới đây là danh sách các hạng mục công việc (todo list) cùng trạng thái thực thi hiện tại.

---

## 🗺️ Tình Trạng Các Trụ Cột Chiến Lược

### 🚀 Trụ Cột 1: Hệ Quản Trị Đa Mã Số Thuế (Multi-MST Profile Manager)
- [x] **Sprint 1.1 (Thiết kế Model & Di trú)**: Thiết kế bảng TaxpayerProfile và tự động cập nhật taxpayer_mst vào bảng Invoice.
- [x] **Sprint 1.2 (Quản lý Profiles & Switcher UI)**: Xây dựng API GET/POST/DELETE /api/profiles và dropdown Switcher trên Navbar.
- [x] **Sprint 1.3 (Multi-Queue Crawler)**: Nâng cấp tiến trình chạy ngầm để hỗ trợ crawl song song/tuần tự cho tất cả MST.

### 🛡️ Trụ Cột 2: Chỉ Số Rủi Ro Thuế Độc Quyền (T-Score & Tax Compliance Rating)
- [x] **Mở rộng Model**: Thêm các cột due_date, paid_date, t_score, t_rating vào bảng Invoice (invoices/models.py).
- [x] **Engine Tính Toán**: Thiết lập logic tính điểm T-Score dựa trên trạng thái MST GDT, chậm ký số, chênh lệch toán học, và rủi ro thanh toán bằng tiền mặt (invoices/service.py).
- [x] **Cơ chế Tự Động Di Trú (Live Migration)**: Thêm kiểm tra cột động trong SQLite khi khởi chạy (app.py).
- [x] **Tích hợp Quy Trình**: Gắn kết quả tính toán T-Score vào API điều chỉnh hóa đơn, import hóa đơn và hậu kiểm AI.
- [x] **Kiểm thử Unit Test**: Xây dựng bộ test tests/test_tscore.py phủ đầy đủ các điều kiện tính điểm T-Score.

### 🤖 Trụ Cột 4: AI Agents Tự Trị Hoạt Động Chạy Ngầm (Autonomous Invoicing Agents)
- [x] **Sprint 4.1 (Background Worker)**: Tích hợp APScheduler hoặc luồng polling SchedulerThread kiểm tra thời gian 23:00 hàng ngày, tự động quét hóa đơn chưa kiểm toán và chạy AI Audit (invoices/scheduler.py).
- [x] **Sprint 4.2 (Telegram Alert Bot & SMTP Email Alert)**:
  - [x] Gửi cảnh báo thời gian thực qua Telegram khi điểm rủi ro T-Score < 50.
  - [x] Gửi cảnh báo qua SMTP Email với định dạng HTML đính kèm danh sách lỗi.
  - [x] Tích hợp cấu hình Telegram Bot Token & Chat ID mã hóa AES-256 vào SystemConfig và thiết lập UI tương ứng (invoices.html, main.js).
- [x] **Sprint 4.3 (Nâng Cấp Chatbot NLP & Text-to-SQL)**:
  - [x] Thiết lập bộ phân tích ý định truy vấn (intent classifier) sử dụng mô hình Gemma-4/Ollama cục bộ.
  - [x] Xây dựng SQL Parser an toàn chỉ cho phép truy vấn SELECT để tránh SQL Injection.
  - [x] Kết xuất báo cáo số liệu dạng bảng biểu thông qua ngôn ngữ tự nhiên.

### ☁️ Trụ Cột 3: Tự Động Sao Lưu Đám Mây & Kết Nối Hệ Sinh Thái (Cloud Sync & Integration)
- [x] **Sprint 3.1 (Đồng Bộ Hóa Google Drive / OneDrive)**:
  - [x] Thiết lập luồng xác thực OAuth2 Offline Refresh Flow cho cả Google Drive API và Microsoft Graph API.
  - [x] Mã hóa refresh_token bằng AES-256 để lưu trữ an toàn trong DB.
  - [x] Tạo module CloudSyncService để tự động upload tệp XML/PDF theo phân cấp /HoaDon_DienTu/[MST]/[Năm]/[Tháng]/.
  - [x] Viết bộ unit test tests/test_cloud_sync.py đạt tỷ lệ bao phủ >= 85%.
- [x] **Sprint 3.2 (Bộ Kết Nối ERP & Webhook Hub)**:
  - [x] Xây dựng module xuất tệp chứng từ tương thích MISA SME (Excel/XML) và bút toán kép Odoo (CSV).
  - [x] Xây dựng Webhook Dispatcher gửi sự kiện invoice.downloaded và invoice.audited kèm chữ ký bảo mật HMAC-SHA256.

---

## 📅 Kế Hoạch Thực Thi Từng Bước (Todo List)

### 🚀 Giai Đoạn 1: Hoàn Thiện Trụ Cột 3 (Cloud Sync & ERP Integration)
- [x] **Task 1**: Tạo module invoices/cloud_service.py để tích hợp Google Drive và OneDrive API.
- [x] **Task 2**: Bổ sung cấu hình OAuth2 của Google Drive / OneDrive vào UI cài đặt và invoices/routes.py.
- [x] **Task 3**: Triển khai trigger upload tệp XML/PDF sau khi crawl hóa đơn thành công.
- [x] **Task 4**: Viết unit test cho cloud_service và tích hợp vào test suite.
- [x] **Task 5**: Triển khai invoices/erp_service.py hỗ trợ xuất file Excel MISA và CSV Odoo.
- [x] **Task 6**: Phát triển module Webhook Dispatcher gửi sự kiện với chữ ký HMAC-SHA256.

### 🚀 Giai Đoạn 2: Hoàn Thiện Trụ Cột 4 (Chatbot NLP & Text-to-SQL)
- [x] **Task 7**: Cải tiến chatbot hiện tại tại invoices/ai_service.py để hỗ trợ phân loại ý định (Intent Classification).
- [x] **Task 8**: Viết SQL Generator an toàn chuyển đổi từ tiếng Việt tự nhiên sang câu lệnh SQLite SELECT.
- [x] **Task 9**: Tích hợp giao diện Chatbot NLP vào tab Trợ lý AI trên frontend.

### 🚀 Giai Đoạn 3: Kiểm Thử Toàn Diện & Đóng Gói (Sprint 5.0)
- [x] **Task 10**: Thực hiện kiểm thử tích hợp liên thông đa MST cùng các tác vụ nền đám mây.
- [x] **Task 11**: Kích hoạt WAL Mode cho SQLite để xử lý tranh chấp tài nguyên đọc/ghi.
- [x] **Task 12**: Cập nhật tài liệu kỹ thuật và API spec chi tiết.

### 🚀 Giai Đoạn 4: Trụ Cột 1 - Hệ Quản Trị Đa Mã Số Thuế (Multi-MST Profile Manager)
- [x] **Task 13**: Thiết kế model TaxpayerProfile và liên kết taxpayer_mst vào bảng invoice.
- [x] **Task 14**: Phát triển các API GET/POST/DELETE /api/profiles và logic mã hóa mật khẩu đối xứng AES-256.
- [x] **Task 15**: Tích hợp UI Switcher trên Navbar và cập nhật bộ lọc đa doanh nghiệp.

### 🚀 Giai Đoạn 5: Phòng Chống Gian Lận Thuế Nâng Cao (v2.1.0 Roadmap)
- [x] **Task 16 (US-050)**: Tích hợp GDT Supplier Blacklist và khấu trừ T-Score về 0 kèm cảnh báo CRITICAL_BLACKLIST_ALERT.
- [x] **Task 17 (US-051)**: Phát triển bộ giám sát tính toàn vẹn chữ ký số ở cấp độ node XML (Node-Level Cryptographic Tampering Auditor) cảnh báo CRITICAL_SIGNATURE_TAMPER.

### 🚀 Giai Đoạn 6: Tích Hợp Hệ Thống Kế Toán Nâng Cao (v2.2.0 Roadmap)
- [x] **Task 18 (US-052)**: Xác thực, chạy thử nghiệm và chuyển trạng thái ERP Double-Entry Journal Auto-Poster sang `implemented`.

### 🚀 Giai Đoạn 7: Trí Tuệ Thuế Doanh Nghiệp & Tự Động Hóa Đa MST (v3.0.0 Roadmap)
- [x] **Task 19 (US-053)**: Phát triển Agent tự động đồng bộ hóa hóa đơn thời gian thực (Real-Time GDT Invoice Synchronization Agent).
- [x] **Task 20 (US-054)**: Xây dựng bộ tự động soạn thảo giải trình thuế bằng AI (AI Tax Optimization & Audit Mitigation Planner).
- [x] **Task 21 (US-055)**: Thiết lập bộ kiểm toán thuế nhà thầu nước ngoài và đa ngoại tệ (Cross-Border E-Commerce & Multi-Currency VAT Auditor).

### 🚀 Giai Đoạn 8: Hoàn Thuế GTGT Thông Minh & Bảo Vệ Hồ Sơ (v4.2.0 Roadmap)
- [x] **Task 22 (US-075)**: Phát triển VAT Refund Eligibility & Policy Engine tự động phân tích hóa đơn và rủi ro.
- [x] **Task 23 (US-076)**: Xây dựng các API endpoint tính toán hoàn thuế `/api/reports/vat-refund-eligibility` và tạo hồ sơ.
- [x] **Task 24 (US-077)**: Tích hợp RAG soạn Giấy đề nghị hoàn trả khoản thu NSNN (Mẫu 01/HT) và báo cáo phòng vệ AI.
- [x] **Task 25 (US-078)**: Thiết kế Widget Hoàn thuế GTGT phong cách Glassmorphism trực quan hóa tỷ lệ xuất khẩu và tiến độ.

### 🚀 Giai Đoạn 9: Enterprise Tax Compliance Orchestrator & Multi-Tenant Scaling (v9.0.0 Roadmap)
- [x] **Task 26 (US-120)**: Phát triển bộ thông dịch và định nghĩa quy tắc kiểm toán tùy biến (Dynamic Rulebook DSL Engine).
- [x] **Task 27 (US-121)**: Xây dựng công cụ lập bản đồ thuế đa khu vực tài phán và quy đổi VND/USD/EUR (Multi-Jurisdictional Tax Mapper).
- [x] **Task 28 (US-122)**: Triển khai hàng đợi sự kiện bất đồng bộ phát bản tin đột biến hóa đơn (High-Throughput PubSub Event Streamer).
- [x] **Task 29 (US-123)**: Tích hợp Webhook Hub bảo mật bằng chữ ký HMAC-SHA256 và cơ chế tự động thử lại (Signed Webhooks with Retry).
- [x] **Task 30 (US-124)**: Tối ưu hiệu năng truy vấn chỉ số Dashboard qua bộ nhớ đệm kết hợp SQLite WAL (Hybrid Memory Caching Layer).
- [x] **Task 31 (US-125)**: Xây dựng tiến trình nén và phân vùng lưu trữ hóa đơn lịch sử tự động (Zero-Downtime Historical Data Archiver).

### 🚀 Giai Đoạn 10: Enterprise Tax Advisory RAG Pro & Multi-Tenancy Orchestrator (v10.0.0 Roadmap)
- [x] **Task 32 (US-130)**: Triển khai dynamic SQL router (`TenantRoutingSession`) tự động cô lập tệp SQLite `tenant_<mst>.db` dựa trên `session["tax_code"]`.
- [x] **Task 33 (US-131)**: Xây dựng cơ chế tự động bootstrap schema (đồng bộ hóa models) cho CSDL Tenant mới tạo.
- [x] **Task 34 (US-132)**: Phát triển dịch vụ AI RAG Pro luật thuế ngoại tuyến (kết nối Ollama cục bộ) và lưu lịch sử hội thoại 10 tin nhắn.
- [x] **Task 35 (US-133)**: Triển khai bảng đề xuất hiệu chỉnh `InvoiceCorrectionProposal` và cơ chế AI Auditor đề xuất nháp sửa đổi.
- [x] **Task 36 (US-134)**: Thiết lập bộ lọc chữ ký số và danh sách đen MST chặn cứng gian lận hóa đơn tại cổng import XML.

### 🚀 Giai Đoạn 11: Enterprise Security Audit Ledger, GDT Portal Sync Resiliency & Tax Risk Analytics (v11.0.0 Roadmap)
- [ ] **Task 37 (US-140)**: Xây dựng bảng ghi nhật ký bảo mật `SecurityAuditLog` lưu trữ log hoạt động đa doanh nghiệp.
- [ ] **Task 38 (US-141)**: Phát triển giao diện tra cứu Audit Trail Viewer và xuất báo cáo CSV/PDF hoạt động bảo mật.
- [ ] **Task 39 (US-142)**: Triển khai hàng đợi đồng bộ bất đồng bộ `ResilientSyncQueue` và scheduler chạy ngầm song song đa MST.
- [ ] **Task 40 (US-143)**: Thiết kế widget và API giám sát sức khỏe solver (`/api/sync/health`) trực quan hóa hiệu suất giải CAPTCHA.
- [ ] **Task 41 (US-144)**: Phát triển Bảng điểm rủi ro Thuế (Tax Risk Scoreboard) tổng hợp lỗi cảnh báo kiểm toán và biểu đồ phân bổ.
- [ ] **Task 42 (US-145)**: Triển khai xuất báo cáo xác thực chữ ký SHA-256 (Signed Compliance Report Exporter) dạng PDF/Excel.

### 🚀 Giai Đoạn 12: Smart Cash Flow Forecasting, AI Tax Optimization & Cross-Tenant Consolidated Analytics (v12.0.0 Roadmap)
- [ ] **Task 43 (US-150)**: Xây dựng mô đun và API dự báo dòng tiền 30/60/90 ngày kết hợp nghĩa vụ thuế.
- [ ] **Task 44 (US-151)**: Thiết kế giao diện mô phỏng tình huống (Scenario Simulator) cho phép stress-test dòng tiền.
- [ ] **Task 45 (US-152)**: Triển khai công cụ kiểm toán thuế TNDN (CIT Deduction Auditor Engine) tự động phát hiện chi phí không hợp lệ.
- [ ] **Task 46 (US-153)**: Phát triển bảng khuyến nghị điều chỉnh thuế TNDN (Deduction Advisory Panel) dẫn chiếu thông tư quy định.
- [ ] **Task 47 (US-154)**: Phát triển giao diện tổng hợp đa MST (Cross-Tenant Consolidated Dashboard) phục vụ tập đoàn doanh nghiệp.
- [ ] **Task 48 (US-155)**: Thiết lập xuất báo cáo Slide tóm tắt quản trị tập đoàn dạng PowerPoint/PDF có chữ ký số.

### 🚀 Giai Đoạn 13: Smart Notification Engine, Advanced Document Intelligence & API Gateway Integration Hub (v13.0.0 Roadmap)
- [ ] **Task 49 (US-160)**: Xây dựng hệ thống cảnh báo hạn nộp thuế tự động (Tax Deadline Alerter) theo lịch tài chính Việt Nam.
- [ ] **Task 50 (US-161)**: Triển khai công cụ quét bất thường và đẩy thông báo thời gian thực (Anomaly Alert Engine) khi import hóa đơn.
- [ ] **Task 51 (US-162)**: Phát triển pipeline OCR xử lý hóa đơn ảnh/scan (Photo Invoice OCR Pipeline) với ddddocr cục bộ.
- [ ] **Task 52 (US-163)**: Thiết kế bộ phân loại tài liệu thông minh (Smart Document Classifier) tự động gợi ý danh mục chi phí.
- [ ] **Task 53 (US-164)**: Triển khai Cổng API REST phiên bản v1 (Versioned REST API Gateway) với xác thực API Key và rate limiting.
- [ ] **Task 54 (US-165)**: Phát triển Marketplace tích hợp và Sổ đăng ký Webhook (Integration Marketplace & Webhook Registry).

### 🚀 Giai Đoạn 14: AI Tax Audit Simulation, Automated Transfer Pricing Compliance & Multi-Currency Treasury Management Hub (v14.0.0 Roadmap)
- [ ] **Task 55 (US-170)**: Xây dựng trình giả lập thanh tra thuế (Tax Audit Simulation Engine) chấm điểm rủi ro T-Score nâng cao có trọng số.
- [ ] **Task 56 (US-171)**: Phát triển panel khuyến nghị giải trình luật thuế (Audit Mitigation Adviser) và soạn thảo văn bản giải trình mẫu DOCX/PDF.
- [ ] **Task 57 (US-172)**: Triển khai bộ nhận diện giao dịch liên kết (Related Party Transaction Detector) kiểm tra EBITDA và giới hạn lãi vay.
- [ ] **Task 58 (US-173)**: Xây dựng wizard tự động lập Hồ sơ quốc gia xác định giá chuyển nhượng (Transfer Pricing Local File Scaffolder).
- [ ] **Task 59 (US-174)**: Phát triển bộ đối chiếu ngoại tệ ngân quỹ (Multi-Currency Treasury Reconciler) quy đổi VND sử dụng tỷ giá VCB hàng ngày.
- [ ] **Task 60 (US-175)**: Triển khai panel kiểm toán tuân thủ thuế nhà thầu nước ngoài (Foreign Contractor Tax Compliance Auditor) cho nhà cung cấp quốc tế.

### 🚀 Giai Đoạn 15: Automated Corporate Income Tax (CIT) Finalization, Visual Scenario Modeler & Intelligent XML Schema Expansion (v15.0.0 Roadmap)
- [ ] **Task 61 (US-180)**: Phát triển bộ tính toán CIT tự động và xuất tờ khai quyết toán thuế mẫu 03/TNDN (CIT Calculation & Form 03/TNDN Scaffolder) tương thích HTKK.
- [ ] **Task 62 (US-181)**: Thiết kế giao diện mô phỏng kịch bản tối ưu thuế TNDN (CIT Scenario Modeler & Stress-Tester) trực quan hóa các biến số.
- [ ] **Task 63 (US-182)**: Xây dựng bộ mở rộng schema XML động trích xuất metadata ngành đặc thù (Schema Extension Engine for Custom Fields).
- [ ] **Task 64 (US-183)**: Phát triển bộ lọc dữ liệu metadata động và kết xuất báo cáo Excel tùy chỉnh (Dynamic Metadata Filter & Report Generator).
- [ ] **Task 65 (US-184)**: Triển khai luồng phê duyệt nội bộ đa cấp và ký số hóa đơn outgoing (Multi-Signature Approval Workflows).
- [ ] **Task 66 (US-185)**: Thiết lập sổ cái băm liên kết (mock Blockchain-Based Invoice Integrity Ledger) xác thực tính toàn vẹn của dữ liệu hóa đơn.

### 🚀 Giai Đoạn 16: Vietnamese E-Invoice Customs & Import-Export Duty Audit Hub, PIT & Social Insurance Audit Engine, and Secure E-Invoice Archiving & TSA Cryptographic Vault (v16.0.0 Roadmap)
- [ ] **Task 67 (US-190)**: Phát triển bộ phân tích tờ khai hải quan XML và tính thuế xuất nhập khẩu (Customs XML Parser & Import-Export Duty Calculator).
- [ ] **Task 68 (US-191)**: Xây dựng panel đối chiếu tờ khai hải quan và hóa đơn GTGT hàng nhập khẩu (Customs-to-Invoice Matcher & Discrepancy Detector).
- [ ] **Task 69 (US-192)**: Triển khai công cụ kiểm toán tuân thủ bảng lương bảo hiểm xã hội và thuế TNCN (Payroll & Labor Contract Compliance Audit Engine).
- [ ] **Task 70 (US-193)**: Thiết kế wizard tự động quyết toán thuế TNCN năm và xuất XML mẫu 05/QTT-TNCN (Automated PIT Finalizer & Form 05/QTT-TNCN Scaffolder).
- [ ] **Task 71 (US-194)**: Xây dựng kho lưu trữ số hóa đơn bảo mật mã hóa AES-256 tuân thủ Nghị định 123 (Decree 123 Compliant Digital Vault & XML Archiver).
- [ ] **Task 72 (US-195)**: Phát triển trình xác thực chữ ký số dài hạn hóa đơn và dấu thời gian TSA (Long-Term Signature & TSA Validator).

### 🚀 Giai Đoạn 17: Statutory Accounting, Corporate Banking Reconciliation & Multi-Channel E-Commerce Tax Sync (v17.0.0 Roadmap)
- [ ] **Task 73 (US-200)**: Tự động lập Báo cáo tài chính (BCTC) chuẩn VAS mẫu B01, B02, B03-DN tương thích HTKK (Statutory Financial Statements Scaffolder).
- [ ] **Task 74 (US-201)**: Triển khai công cụ kiểm tra tính toàn vẹn và đối chiếu chéo số phát sinh sổ cái với Hóa đơn XML (Trial Balance & Ledger Integrity Auditor).
- [ ] **Task 75 (US-202)**: Phát triển tính năng sinh Giấy nộp tiền vào Ngân sách Nhà nước mẫu 711/MB và QR nộp thuế nhanh (GDT Tax Payment Slip Scaffolder).
- [ ] **Task 76 (US-203)**: Triển khai bộ đối soát dòng tiền và nhật ký giao dịch ngân hàng thương mại với hóa đơn (Corporate Banking Transaction Reconciler).
- [ ] **Task 77 (US-204)**: Tích hợp API và đồng bộ hóa đơn dịch vụ, doanh thu sàn thương mại điện tử Shopee, Lazada, TikTok (E-Commerce Seller Portal Sync).
- [ ] **Task 78 (US-205)**: Thiết kế động cơ đối soát tự động doanh thu sàn TMĐT với hóa đơn bán lẻ đã phát hành (Multi-Channel Revenue & Tax Matcher).



