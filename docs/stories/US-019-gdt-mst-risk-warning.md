# US-019: GDT MST Status Verification and Early Warning Risk System

## Status

implemented

## Lane

high-risk

## Product Contract

The application must check the tax registration status (active, suspended, closed, not found) of partner business MSTs. If a partner is suspended, closed, or not found in the tax database, the system will raise an audit warning badge to prevent potential transactions with non-compliant entities.

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)
- [docs/product/invoices.md](file:///d:/LearnAnyThing/Webapp%20XML/docs/product/invoices.md)

## Acceptance Criteria

- [x] A new service `invoices/mst_service.py` is created with `check_mst_status(mst: str) -> dict`.
- [x] Mock mode matches predefined partners: Cong ty A (ACTIVE), Cong ty B (CLOSED), Cong ty C (SUSPENDED).
- [x] Live mode performs standard HTML scraping on `https://masothue.com` (or similar lookup page) and parses the tax status.
- [x] Statuses are cached in `invoices_db.json` under each partner to avoid excessive requests.
- [x] Smart Audit engine runs a **7th rule** verifying that the seller MST is not suspended or closed.
- [x] UI displays an MST status badge in the Partner Directory tab (Green/Yellow/Red).
- [x] A "Tra cứu live" (Verify) button in the Partner Directory forces an on-demand status check via a new endpoint `GET /api/partners/<mst>/status`.
- [x] Details drawer UI displays the 7th smart audit check result for MST status.

## Design Notes

- **Statuses**:
  - `ACTIVE`: `"Đang hoạt động (đã được cấp MST)"`
  - `SUSPENDED`: `"Tạm ngừng hoạt động"`
  - `CLOSED`: `"Ngừng hoạt động, đã đóng MST"`
  - `NOT_FOUND`: `"Mã số thuế không tồn tại"`
- **API**: `GET /api/partners/<mst>/status` returning `{"mst": mst, "status": status}`.
- **Cache**: Cached inside `invoices_db.json` partners array: `{"mst": "...", "mst_status": "...", "mst_last_checked": "..."}`.
