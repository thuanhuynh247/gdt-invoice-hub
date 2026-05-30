# Khuym Context: Version 13.0.0 Smart Notification Engine, Advanced Document Intelligence & API Gateway Integration Hub

Quyết định thiết kế và phạm vi nghiệp vụ cho việc triển khai Phiên bản 13.0.0.

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `v13_roadmap`
* **Quy mô (Scope)**: `Deep` (Lộ trình chiến lược mở rộng năng lực cảnh báo thông minh, xử lý tài liệu ảnh, và tích hợp mở với hệ sinh thái bên ngoài).
* **Phân loại Phân hệ (Domain Types)**:
  - `SEE`: Thanh cảnh báo (Alert Bell), Bảng quản lý Webhook, Giao diện xem trước OCR, Panel phân loại tài liệu.
  - `CALL`: Các API: `/api/notifications/deadlines`, `/api/notifications/alerts`, `/api/invoices/ocr-upload`, `/api/v1/invoices`, `/api/v1/docs`.
  - `RUN`: Tiến trình quét cảnh báo bất thường nền, pipeline OCR xử lý hình ảnh hóa đơn, cơ chế gửi webhook bất đồng bộ.
  - `ORGANIZE`: Bảng dữ liệu `NotificationAlert`, `WebhookSubscription`, `APIKey`, cấu trúc OpenAPI spec.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu Lộ trình v13]**: Triển khai gói giải pháp v13.0.0 tích hợp ba trụ cột: Hệ thống Thông báo Chủ động (Smart Notifications cho deadline thuế và cảnh báo bất thường), Xử lý Tài liệu Thông minh (OCR Pipeline cho hóa đơn ảnh/scan và AI Document Classifier), và Cổng API Mở (Versioned REST API Gateway v1 với xác thực API Key và Marketplace quản lý webhook).
* **D2 [Lịch tài chính Việt Nam]**: Bộ tính deadline sẽ tuân thủ lịch nộp thuế theo quy định hiện hành: VAT khai theo quý (nộp chậm nhất ngày cuối tháng kế tiếp quý), CIT tạm tính quý (cùng kỳ hạn VAT), CIT quyết toán năm (chậm nhất 31/03 năm sau). Hệ thống sẽ tự động tính toán dựa trên kỳ thuế hiện tại.
* **D3 [OCR Zero-Cloud]**: Pipeline OCR hóa đơn ảnh sẽ ưu tiên sử dụng thư viện cục bộ (ddddocr + Tesseract fallback) để xử lý hoàn toàn trên máy tính người dùng, không gửi hình ảnh hóa đơn lên bất kỳ cloud nào nhằm bảo mật dữ liệu tài chính.
* **D4 [API Key không dùng OAuth]**: API Gateway v1 sẽ sử dụng cơ chế API Key đơn giản (mã thông báo 256-bit lưu bảng `APIKey`) thay vì OAuth2 để giảm thiểu độ phức tạp triển khai. Rate limiting sẽ dùng bộ đếm in-memory theo IP + API key.
* **D5 [Webhook Idempotency]**: Mỗi webhook delivery sẽ đi kèm `X-Delivery-ID` duy nhất và `X-Signature` HMAC-SHA256. Hệ thống ghi lại toàn bộ lịch sử delivery (status code, latency, retry count) để audit.

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  - `templates/base.html` (Alert bell icon, notification dropdown, API docs link)
  - `templates/settings.html` (Webhook management panel, API key management)
  - `static/js/main.js` (Polling/SSE cho alert badge, OCR preview modal, webhook form)
* **Nghiệp vụ (RUN / CALL / ORGANIZE)**:
  - `invoices/models.py` (Khai báo `NotificationAlert`, `WebhookSubscription`, `APIKey`, `DocumentClassification`)
  - `invoices/routes.py` (Đăng ký tất cả endpoint mới)
  - `invoices/service.py` (Thuật toán tính deadline thuế, scanner cảnh báo, classifier)
  - `invoices/ocr_pipeline.py` (Module OCR xử lý ảnh hóa đơn → structured data)
  - `invoices/api_gateway.py` (Middleware xác thực API key, rate limiter, OpenAPI generator)
  - `invoices/webhook_dispatcher.py` (Bộ phát webhook bất đồng bộ có retry)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)

* Push notification qua Firebase/APNs cho mobile app. (Hoãn lại, chỉ hỗ trợ in-app alert badge và email digest trong v13).
* OCR sử dụng Google Vision API hoặc Azure Document Intelligence. (Hoãn lại, ưu tiên zero-cloud local OCR).
* OAuth2/OIDC cho API Gateway. (Hoãn lại, sử dụng API Key đơn giản cho v1; có thể nâng cấp OAuth2 ở v14+).
* GraphQL endpoint. (Hoãn lại, REST JSON là tiêu chuẩn cho v1 gateway).
