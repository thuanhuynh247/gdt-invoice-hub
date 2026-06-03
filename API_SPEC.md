# API Specification

## Status

Tai lieu nay mo ta API local cua webapp theo MVP hien tai. Tinh den `2026-05-21`, app da hardcode cac endpoint live cho captcha, auth JWT va invoice list sau khi doi chieu production bundle cua `gdt.gov.vn`.

## Authentication

### `POST /api/auth/login`

- Purpose: Dang nhap va tao session local.
- Live mode:
  - Server goi `POST https://hoadondientu.gdt.gov.vn/api/security-taxpayer/authenticate`
  - body upstream: `username`, `password`, `cvalue`, `ckey`
- Body:
  ```json
  {
    "username": "demo",
    "password": "secret",
    "captcha": "MOCK-1234"
  }
  ```
- Success:
  ```json
  {
    "status": "success",
    "message": "Dang nhap thanh cong.",
    "expires_at": "2026-05-20T12:00:00+00:00",
    "mode": "mock"
  }
  ```
- Errors:
  - `401`: thieu thong tin hoac login fail

### `GET /api/auth/captcha`

- Purpose: Lay captcha SVG va luu `ckey` trong session server.
- Success:
  ```json
  {
    "image_svg": "<svg ...>",
    "mode": "live"
  }
  ```

### `POST /api/auth/logout`

- Purpose: Xoa session hien tai.
- Success:
  ```json
  {
    "status": "success",
    "message": "Da dang xuat."
  }
  ```

### `GET /api/session-status`

- Purpose: Frontend check session con han hay khong.
- Success:
  ```json
  {
    "logged_in": true,
    "username": "demo",
    "expires_in": 1700,
    "warning_threshold_seconds": 60
  }
  ```

## Invoice Endpoints

### `GET /api/invoices`

- Query:
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
  - `cancelled_only=true|false`
  - `direction=purchase|sold`
- Success:
  ```json
  {
    "total_count": 3,
    "invoices": [
      {
        "id": "INV-2026-0501",
        "date": "2026-05-01",
        "amount": 1500000,
        "status": "valid",
        "issuer": "Cong ty A",
        "description": "Hoa don dau vao thang 5",
        "is_cancelled": false,
        "cancellation_date": null,
        "cancellation_reason": null
      }
    ]
  }
  ```
- Errors:
  - `400`: date invalid
  - `401`: chua dang nhap
  - `503`: live integration chua san sang hoac GDT tra loi loi

### `GET /api/cancelled-invoices`

- Same query as `/api/invoices`
- Success:
  ```json
  {
    "total_count": 1,
    "cancelled_invoices": [
      {
        "id": "INV-2026-0508",
        "is_cancelled": true,
        "cancellation_reason": "Sai thong tin nguoi mua"
      }
    ]
  }
  ```

### `GET /api/invoices/<invoice_id>/download`

- Purpose: Tai XML cho mot hoa don.
- Response:
  - `200` with `application/xml`
  - `Content-Disposition: attachment`
- Live mode:
  - route upstream: `GET https://hoadondientu.gdt.gov.vn/api/{query|sco-query}/invoices/export-xml`
  - params upstream: `nbmst`, `khhdon`, `shdon`, `khmshdon`
  - route chi goi live khi row co `hsgoc`
  - file co the tra ve `.zip` thay vi `.xml`
  - chua co credential that de xac nhan end-to-end

### `GET /api/export-excel`

- Query:
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
  - `cancelled_only=true|false`
  - `direction=purchase|sold`
- Response:
  - `200` with XLSX binary download

## Misc

### `GET /api/config`

- Success:
  ```json
  {
    "mock_mode": true,
    "locale": "vi-VN"
  }
  ```

### `GET /health`

- Success:
  ```json
  {
    "status": "ok",
    "mode": "mock"
  }
  ```

## Next-Gen AI & Analytics APIs

### `POST /api/ai/chat/sessions`
- Purpose: Tạo phiên trợ lý hội thoại AI mới.
- Response:
  ```json
  {
    "id": "uuid-string",
    "title": "Cuộc hội thoại mới",
    "created_at": "YYYY-MM-DD HH:MM:SS"
  }
  ```

### `POST /api/ai/chat/sessions/<session_id>/message`
- Purpose: Gửi tin nhắn và nhận phản hồi của Trợ lý AI (hỗ trợ phân loại ý định & Text-to-SQL tự động có kiểm duyệt an toàn).
- Body:
  ```json
  {
    "message": "Tính tổng doanh thu hóa đơn bán ra?"
  }
  ```
- Success Response:
  ```json
  {
    "user_message": {
      "id": 1,
      "role": "user",
      "content": "Tính tổng doanh thu hóa đơn bán ra?",
      "created_at": "YYYY-MM-DD HH:MM:SS"
    },
    "assistant_message": {
      "id": 2,
      "role": "assistant",
      "content": "Tổng doanh thu bán ra thực tế...\n\n**Truy vấn SQL thực thi:**\n```sql\nSELECT sum(total_amount) FROM invoice WHERE is_cancelled = 0;\n```\n...",
      "created_at": "YYYY-MM-DD HH:MM:SS"
    },
    "session_title": "Tính tổng doanh thu hóa đơn..."
  }
  ```

### `POST /api/invoices/local/<invoice_id>/ai-audit`
- Purpose: Chạy kiểm toán tuân thủ thuế AI cục bộ cho hóa đơn cụ thể.
- Success Response:
  ```json
  {
    "status": "success",
    "warnings": [
      {
        "warning_type": "price_anomaly",
        "explanation": "Đơn giá sản phẩm cao hơn trung bình lịch sử 30%."
      }
    ]
  }
  ```

### `GET /api/analytics/supplier-price-trends`
- Query Parameters: `item_name=Laptop`
- Success Response:
  ```json
  {
    "item_name": "Laptop",
    "trends": [
      {
        "seller_name": "Cong ty A",
        "seller_mst": "123456789",
        "prices": [
          {"date": "2026-05-01", "price": 15000000}
        ]
      }
    ]
  }
  ```

### `GET /api/analytics/vat-forecast`
- Purpose: Dự báo thuế VAT ròng dựa trên hồi quy tuyến tính dữ liệu lịch sử.
- Success Response:
  ```json
  {
    "forecast": [
      {
        "month": "2026-06",
        "projected_vat": 15200000.0
      }
    ]
  }
  ```

## Cloud Sync & ERP Connections

### `GET /api/erp/export/misa`
- Purpose: Xuất báo cáo Excel tương thích định dạng nhập chứng từ của MISA SME.
- Response: File Excel binary download.

### `GET /api/erp/export/odoo`
- Purpose: Xuất bút toán Odoo CSV định dạng kế toán kép.
- Response: File CSV binary download.

