# US-017: Trình Xem Hóa Đơn Điện Tử Mẫu (Interactive Invoice Viewer Modal)

## Status

completed

## Lane

normal

## Product Contract

The application must provide a beautiful, seamless, and interactive full-page/large modal preview of the Vietnamese electronic invoice (red printable layout) when a user requests to view it. It wraps the raw `/api/invoices/<id>/pdf-view` HTML content in a container featuring dynamic controls to print, download XML, or open in a new tab.

## Relevant Product Docs

- `docs/ARCHITECTURE.md`
- `PROGRESS_TRACKER_INVOICE_WEBAPP.md`

## Acceptance Criteria

1. **Trigger Actions**:
   - Double-clicking a search result invoice row opens the viewer modal.
   - Double-clicking a local audited invoice row opens the viewer modal.
   - Clicking the "Xem" button in the local audited table row opens the viewer modal.
   - Clicking "Xem Bản In Hóa Đơn (PDF)" in the invoice details drawer opens the viewer modal.
2. **Interactive Modal (Supabase Dark/Light Glassmorphism)**:
   - Utilizes Bootstrap Modal styled with glassmorphic cards and dynamic theme variables.
   - Includes a loading spinner overlay (`#viewerLoadingOverlay`) while the `<iframe>` is loading its source, and transitions opacity smoothly once loaded.
3. **Dedicated Toolbar**:
   - Left side: Display title ("Trình Xem Hóa Đơn Mẫu"), a badge for the audit status (e.g. `Hợp Lệ` or `Lỗi / Cảnh Báo`), and metadata (`Ký hiệu`, `Số HĐ`).
   - Right side action controls:
     - **Tải XML**: Downloads the raw XML file.
     - **In Hóa Đơn**: Triggers print dialog inside the iframe.
     - **Mở tab mới**: Opens the printable view in a raw new tab for traditional browser handling.
     - **Đóng**: Dismisses the modal.

## Design Notes

- **UI surfaces**:
  - Modal container in `templates/invoices.html`.
  - Trigger bindings and handlers in `static/js/main.js`.
- **API routes involved**:
  - `/api/invoices/<invoice_id>/pdf-view` (iframe src)
  - `/api/invoices/<invoice_id>/download` (xml download link)

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit / Integration | Run pytest to verify all invoice routes (pdf-view, details, downloads) return correct responses and statuses. |
| E2E | Use browser subagent to click, double-click, and verify modal opens and toolbar buttons operate successfully. |

## Harness Delta

None.

## Evidence

- **Unit/Integration Proof**:
  - Ran `.\venv\Scripts\pytest -v` resulting in 56/56 passed tests (including all mock endpoint verifications).
  - Target routes `/api/invoices/<invoice_id>/pdf-view`, `/api/invoices/<invoice_id>/download`, and `/api/invoices/<invoice_id>/details` fully validated.
- **E2E/Manual Proof**:
  - Interactive validation performed using browser agent:
    - Login using mock credentials successfully resolved.
    - Double click on invoice rows from search and local audited list correctly opens the modal overlay.
    - Spinner loading state and iframe content loading verified.
    - Toolbar operations (XML download, print trigger, tab fallback) successfully tested.
  - Recording saved at: `invoice_viewer_modal_verification_1779416121581.webp`
  - Feedback screenshots:
    - [Audited Invoice Detail](file:///C:/Users/THUAN/.gemini/antigravity/brain/82b7ad4b-d075-4465-a62c-c996958717a5/.system_generated/click_feedback/click_feedback_1779416356536.png)
    - [Viewer Modal View](file:///C:/Users/THUAN/.gemini/antigravity/brain/82b7ad4b-d075-4465-a62c-c996958717a5/.system_generated/click_feedback/click_feedback_1779416373496.png)

