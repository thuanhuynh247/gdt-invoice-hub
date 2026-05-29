# Design: US-025 Database Persistence and SQLite Migration

## Domain Model

Entities represented in SQLite:
- **Invoice**: Core invoice record. Contains identification, timestamps, seller/buyer info, total sums, signature metadata, validation status, audit warning lists, and import metadata.
- **LineItem**: Specific items/services listed on an invoice. Linked via foreign key to the parent `Invoice`.
- **Partner**: Extracted vendor metadata containing MST, vendor name, address, tax registration status, and cache update timestamps.
- **SystemConfig**: Dynamic application key-value configuration values (such as SMTP details, time intervals, GDT username/passwords).
- **SchedulerLog**: Historical logs of scheduler runs.

## Data Model

### SQLite Tables & Columns

```mermaid
erDiagram
    SYSTEM_CONFIG {
        string key PK
        string value
    }
    SCHEDULER_LOG {
        integer id PK
        string timestamp
        string status
        string details
    }
    PARTNER {
        string mst PK
        string name
        string address
        string mst_status
        string mst_last_checked
    }
    INVOICE {
        string id PK "format: seller_mst-symbol-number"
        string filename
        string invoice_type
        string template_code
        string symbol
        string number
        string date
        string currency
        string seller_name
        string seller_mst
        string seller_address
        string seller_phone
        string buyer_name
        string buyer_mst
        string buyer_address
        float amount_before_tax
        float tax_amount
        float total_amount
        boolean has_signature
        string signing_date
        string payment_method
        boolean is_cancelled
        string cancellation_date
        string cancellation_reason
        text warnings "JSON-serialized list of audit warning strings"
        text notes
        string imported_at
        string updated_at
        string import_status
    }
    LINE_ITEM {
        integer id PK
        string invoice_id FK
        string item_name
        string unit
        float quantity
        float unit_price
        float amount_before_tax
        string tax_rate
        float tax_amount
    }
    INVOICE ||--o{ LINE_ITEM : has
```

### Constraints & Concurrency
- **Foreign Keys**: `line_item.invoice_id` references `invoice.id` with `ON DELETE CASCADE`.
- **WAL Mode**: Executed on database connection to optimize concurrent transactions:
  ```sql
  PRAGMA journal_mode=WAL;
  PRAGMA synchronous=NORMAL;
  ```
- **Transaction Retry**: To handle potential database locks under extreme concurrent test runs, a simple retry handler or transaction context decorator is used for writing.

## Interface Contract

All HTTP APIs remain unchanged. The backend query logic returns identical JSON structures to the frontend AJAX callers:
- `GET /api/settings` and `POST /api/settings`
- `GET /api/settings/logs`
- `GET /api/invoices` and `POST /api/invoices/import`
- `/api/invoices/<id>/details`

## Observability

All database initialization and migration steps write logging info to Flask's app logs. Failed migrations trigger diagnostic messages.
