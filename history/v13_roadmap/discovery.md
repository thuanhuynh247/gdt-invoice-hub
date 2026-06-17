# Discovery - Version 13.0.0: Smart Notification Engine, Advanced Document Intelligence & API Gateway Integration Hub

## Technical Constraints & Facts

1. **Codebase Inclusions**:
   - `invoices/notification_service.py` computes fiscal deadlines and manages persistent compliance alerts.
   - `invoices/ocr_service.py` invokes `ddddocr` or a mock fallback for physical image parsing.
   - `invoices/classifier_service.py` houses keyword rules and historic mappings to resolve expense categories.
   - `invoices/api_gateway.py` implements API Key decorator logic and token-bucket rate limiting.
2. **Key Constraints**:
   - Webhook events are signed using HMAC-SHA256 headers (`X-Hub-Signature`).
   - OCR runs as an async task or returns a draft preview before persistence.
3. **Existing Tests**:
   - `tests/test_ocr_pipeline.py` verifies extraction accuracy, while `tests/test_webhook_hub.py` checks delivery logs.

---

## Structural Discovery & Integration Points
- All business operations are modularized within separate service files under the `invoices/` directory.
- APIs are declared via blueprints inside `invoices/routes.py` to maintain routing modularity.
