# Feasibility Validation: Version 13.0.0 Smart Notification Engine, Advanced Document Intelligence & API Gateway Integration Hub

Báo cáo kết quả kiểm chứng tính khả thi kỹ thuật và ma trận sẵn sàng triển khai cho Version 13.0.0.

---

## 1. Ma trận Khả thi (Feasibility Matrix)

| Phân hệ / Tính năng | Tính khả thi | Phương án chứng minh | Mức độ rủi ro | Trạng thái sẵn sàng |
|---|---|---|---|---|
| **Tax Deadline Alerter** | **100%** | Tính toán dựa trên lịch tài chính Việt Nam (quý/năm) kết hợp `datetime` Python. Hiển thị countdown badge. | Thấp | **READY** |
| **Anomaly Alert Engine** | **100%** | Hook vào luồng import invoice hiện có, kiểm tra T-Score và trigger tạo bản ghi `NotificationAlert`. | Thấp | **READY** |
| **Photo Invoice OCR Pipeline** | **90%** | Sử dụng ddddocr (đã tích hợp) + Tesseract fallback cho text extraction. Layout parsing cần tuning cho format hóa đơn VN. | Trung bình | **READY** |
| **Smart Document Classifier** | **100%** | Keyword-based + historical pattern matching. Không cần model ML phức tạp ở v13. | Thấp | **READY** |
| **Versioned REST API Gateway** | **100%** | Flask Blueprint `/api/v1/` với decorator xác thực API key. OpenAPI spec sinh từ docstring. | Thấp | **READY** |
| **Integration Marketplace** | **100%** | CRUD UI cho `WebhookSubscription` + async dispatcher reuse từ v9 (US-123). | Thấp | **READY** |

---

## 2. Kế hoạch Kiểm thử & Hậu nghiệm (Verification Strategy)

1. **Kiểm thử Tax Deadline (`tests/test_v13_deadline_alerter.py`)**:
   - Giả lập ngày hiện tại ở các thời điểm khác nhau trong quý.
   - Xác minh API trả về đúng deadline kế tiếp với số ngày countdown chính xác.
   - Kiểm tra badge hiển thị đúng mức cảnh báo (30d/15d/7d/overdue).

2. **Kiểm thử Anomaly Alert (`tests/test_v13_anomaly_alerts.py`)**:
   - Import hóa đơn có T-Score < ngưỡng cấu hình.
   - Xác minh bản ghi `NotificationAlert` được tạo với severity đúng.
   - Kiểm tra API phân trang và filter theo severity.

3. **Kiểm thử OCR Pipeline (`tests/test_v13_ocr_pipeline.py`)**:
   - Upload ảnh hóa đơn mẫu (test fixture).
   - Xác minh extraction trả về đúng MST, tên người bán, số tiền.
   - Kiểm tra xử lý ảnh lỗi/mờ trả về error message hợp lý.

4. **Kiểm thử Document Classifier (`tests/test_v13_classifier.py`)**:
   - Gửi hóa đơn với seller name và mô tả line item đã biết.
   - Xác minh classifier gợi ý đúng category với confidence > 0.7.

5. **Kiểm thử API Gateway (`tests/test_v13_api_gateway.py`)**:
   - Gửi request không có API key → 401.
   - Gửi request với API key hợp lệ → 200 + JSON envelope đúng format.
   - Vượt rate limit → 429 Too Many Requests.

6. **Kiểm thử Webhook Registry (`tests/test_v13_webhook_registry.py`)**:
   - Tạo subscription, trigger event, xác minh delivery log ghi nhận đúng status code.
   - Kiểm tra HMAC signature trong header `X-Signature`.
