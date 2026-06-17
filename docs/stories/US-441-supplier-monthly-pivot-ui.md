# Spec: US-441 — Interactive Input Invoice Supplier Monthly Pivot Table Dashboard UI

## Status
implemented

## Lane
high_risk

## Acceptance Criteria
- **Giao diện Tab Partners**:
  - Thêm lựa chọn thứ ba "Bảng Pivot NCC" vào nút chọn chế độ xem `partnerViewMode` (`#viewModePivot`).
  - Cập nhật bo viền các nút bấm để hiển thị liền mạch.
- **Pivot Table Container**:
  - Tạo container `#partnersPivotContainer` hiển thị khi chọn chế độ Pivot.
  - Tích hợp bộ công cụ (Toolbar) gồm:
    - Bộ lọc Năm (`#pivotYearFilter`) mặc định là `2026`.
    - Bộ chọn loại chỉ số hiển thị (`#pivotMetricType`) mặc định là `total_amount`.
    - Ô tìm kiếm nhà cung cấp tức thời (`#pivotSearchInput`).
    - Nút Xuất Excel (`#btnPivotExport`).
- **Lưới hiển thị (Table)**:
  - Bảng cuộn ngang, hỗ trợ sticky columns cho Mã số thuế và Tên NCC.
  - Định dạng hiển thị tiền tệ VNĐ cực kỳ trực quan, các ô bằng 0 hiển thị dấu gạch ngang `-`.
  - Hiển thị dòng tổng cộng ở cuối bảng (`Footer Row`) và cột tổng cộng ở cuối mỗi dòng.
- **Xuất Excel**:
  - Cho phép tải xuống file Excel chứa đúng định dạng ma trận Pivot vừa hiển thị.
