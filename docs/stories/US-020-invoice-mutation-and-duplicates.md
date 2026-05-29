# US-020: Quản lý Trùng Lặp, Xóa và Điều Chỉnh Hóa Đơn Cục Bộ

## Status

implemented

## Lane

normal

## Product Contract
Hệ thống cho phép người dùng kiểm soát hành vi khi nhập hóa đơn trùng lặp (Ghi đè/Bỏ qua), xóa các hóa đơn sai sót khỏi kho cục bộ, và điều chỉnh thông tin hóa đơn (ngày, số tiền, hình thức thanh toán, trạng thái thuế) trực tiếp trên giao diện và tự động cập nhật lại đánh giá Smart Auditing tương ứng.

## Relevant Product Docs

- `docs/ARCHITECTURE.md`
- `docs/FEATURE_INTAKE.md`

## Acceptance Criteria

1. **Duplicate Resolution**: Khi import XML/ZIP hoặc chạy Tải hàng loạt, có tuỳ chọn cấu hình xử lý trùng lặp (`duplicate_strategy` là `"overwrite"` hoặc `"skip"`).
   - Nếu `"overwrite"`, ghi đè bản ghi cũ.
   - Nếu `"skip"`, giữ nguyên bản ghi cũ và trả về trạng thái bỏ qua.
2. **Single Invoice Delete**: Có nút bấm "Xóa" trên từng dòng hóa đơn cục bộ. Khi nhấn và xác nhận, hóa đơn bị loại bỏ khỏi `invoices_db.json` và tệp XML gốc tương ứng trong `data/invoices_xml/` bị xóa hoàn toàn.
3. **Single Invoice Adjustment**: Có nút bấm "Sửa/Điều chỉnh" trên dòng hóa đơn hoặc trong chi tiết Offcanvas. Khi chỉnh sửa:
   - Cho phép cập nhật: Ngày lập, Tên/MST người bán, Tên/MST người mua, Tiền trước thuế, Tiền thuế, Tổng tiền, Hình thức TT, Trạng thái (Gốc, Thay thế, Điều chỉnh, Hủy) và Ghi chú.
   - Khi lưu, chạy lại **Smart Auditing (7 quy tắc)** dựa trên dữ liệu mới điều chỉnh và lưu lại warnings.
   - Cập nhật số liệu đếm trên 4 thẻ thống kê Smart Audit tương ứng thời gian thực.
4. **Validation Proof**: Thêm test coverage kiểm nghiệm cho hành vi ghi đè/bỏ qua, xóa hóa đơn, điều chỉnh hóa đơn và chạy lại smart audit.

## Design Notes

- **API DELETE**: `DELETE /api/invoices/local/<invoice_id>`
- **API PATCH**: `PATCH /api/invoices/local/<invoice_id>`
- **UI Surfaces**:
  - Dropdown cấu hình xử lý trùng lặp trong vùng Drag & Drop/Tải hàng loạt.
  - Nút biểu tượng Bút chì (Sửa/Điều chỉnh) và Thùng rác (Xóa) ở cột hành động của bảng hóa đơn cục bộ.
  - Modal `#adjustInvoiceModal` chứa form nhập thông tin điều chỉnh.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `tests/test_meinvoice.py::test_invoice_duplicate_strategy_and_mutations` |
| Integration | `.\scripts\validate.bat` passes successfully |
| E2E | Manual testing via browser checking deletion and adjustment flow |

## Harness Delta

Không có thay đổi về quy tắc Harness.

## Evidence

- `tests/test_meinvoice.py::test_invoice_duplicate_strategy_and_mutations` verifies the backend business rules for duplicate strategies (`skip`, `overwrite`), deletion of databases/files, patch mutation updates, and recalculation of smart warnings (e.g. non-cash threshold).
- Validation script `.\scripts\validate.bat` run successfully with 64 checks passed.

