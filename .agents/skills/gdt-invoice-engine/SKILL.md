---
name: gdt-invoice-engine
description: Vietnam E-Invoice XML parsing, GDT API synchronization, schema validation, and multi-tenant database pipeline in Webapp XML. Use when modifying XML parsers, GDT sync workers, captcha renewal daemons, invoice deduplication, or multi-tenant database operations.
---

# GDT Invoice Engine Specialist

Manage and optimize the end-to-end electronic invoice (HĐĐT) ingestion pipeline for the Webapp XML platform, covering XML parsing, GDT portal communication, captcha solving queues, and multi-tenant SQLite persistence.

## Core Pipeline Architecture

```
[Raw XML / GDT API]
       │
       ▼
┌──────────────────────────────┐
│  XML Parser & Schema Validator│ (Validates TT78/ND123 tags & signatures)
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Deduplication & Hash Check  │ (SHA256 of Ký hiệu + Số HĐ + MST Người Bán)
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Multi-Tenant SQLite Router  │ (Routes to instance/tenant_<MST>.db)
└──────────────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Compliance DSL Evaluation   │ (Calculates T-Score penalties & anomaly flags)
└──────────────────────────────┘
```

---

## Technical Standards & Rules

### 1. XML Parsing (`invoices/service.py`)
- Parse XML using `defusedxml` or standard `xml.etree.ElementTree` with error recovery.
- Extract required fields:
  - Header: `KHHDon` (Ký hiệu), `SHDon` (Số hóa đơn), `NLap` (Ngày lập), `TTe` (Tiền tệ).
  - Seller: `NBan/MST` (Mã số thuế bên bán), `NBan/Ten` (Tên bên bán), `NBan/DChi` (Địa chỉ).
  - Buyer: `NMua/MST` (Mã số thuế bên mua), `NMua/Ten` (Tên bên mua).
  - Financials: `TgTCThue` (Tổng tiền chưa thuế), `TgTThue` (Tổng tiền thuế), `TgTTMSO` (Tổng thanh toán).
  - Items: List of line items (`THHDVu`, `SLuong`, `DGia`, `TSuat`, `ThTien`).

### 2. Multi-Tenant Database Isolation
- Every database query must resolve the active taxpayer MST context.
- Database files reside in `instance/` or `data/` named `tenant_<MST>.db`.
- SQLite connections must enable WAL mode (`PRAGMA journal_mode=WAL;`) and busy timeout (`PRAGMA busy_timeout=5000;`) to prevent concurrency locks.

### 3. Background Sync & Captcha Daemon (`invoices/sync_queue.py`)
- GDT synchronization jobs must execute in asynchronous worker threads or subprocesses to prevent blocking Flask's HTTP request loop.
- Track queue state in SQLite with job statuses: `PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED`.
- Exponential backoff retry on network throttles (HTTP 429 / 503).

---

## Step-by-Step Execution Workflow

1. **Investigate Code & Schema**:
   - Inspect `invoices/service.py` for parser functions.
   - Inspect `invoices/sync_queue.py` for job queuing logic.

2. **Develop / Patch Logic**:
   - Implement parser enhancements with defensive fallbacks for non-standard XML tags.
   - Maintain deduplication guarantees before executing SQL inserts.

3. **Verify with Pytest Suite**:
   ```bash
   pytest tests/test_meinvoice.py tests/test_v11_sync_resiliency.py -v
   ```

4. **Verify Database Integrity**:
   - Ensure tables `invoices`, `invoice_items`, `sync_jobs`, and `compliance_records` maintain proper foreign key relationships.

---

## Quality Gate Checklist

- [ ] XML parsing handles missing tags and date variations safely.
- [ ] No cross-tenant data leaks (all queries scoped to active MST).
- [ ] Concurrency-safe SQLite WAL mode enforced.
- [ ] All unit and integration tests pass.
