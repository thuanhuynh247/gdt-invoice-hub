# Story Specification: US-207 — SEE - Cải tiến trang Tra cứu Hóa đơn và Bento Grid KPI

## 📋 Context & Business Value
Trang Tra cứu Hóa đơn là trung tâm tương tác chính của ứng dụng. Nhằm cải thiện trải nghiệm người dùng (UX) và tối ưu hóa diện tích hiển thị (UI), trang này cần được nâng cấp cấu trúc Bento Grid KPI sắc nét, bổ sung hiệu ứng hover cao cấp và tối ưu hóa việc phân nhóm dữ liệu phân tích hóa đơn.

---

## 🎯 Acceptance Criteria

### 1. Advanced Bento Grid Layout
- Cải thiện Bento Grid KPI hiển thị trực quan các chỉ số tài chính (Tổng giá trị, Tổng tiền thuế, Hóa đơn hợp lệ, Hóa đơn đã hủy).
- Đảm bảo thiết kế responsive hoàn hảo trên các thiết bị di động, tablet và desktop.

### 2. High-Fidelity UI Styling
- Tích hợp hiệu ứng Glassmorphism tinh tế cho các thẻ thống kê (`stat-card`), bo góc mượt mà (Wise Fintech rounded pill / card).
- Tách biệt rõ ràng các khu vực biểu đồ phân tích và bảng dữ liệu tra cứu để giảm tải lượng thông tin hiển thị (cognitive load).

### 3. Interactive Search Filters
- Cải tiến giao diện của form bộ lọc tìm kiếm: bố trí gọn gàng, tăng cường độ tương phản và thêm các micro-interactions khi rê chuột.

---

## 🛠️ Verification & Test Plan

- **Manual Verification**:
  - Truy cập trang `/invoices` (Tra cứu Hóa đơn) và kiểm tra diện mạo bento grid.
  - Sử dụng các bộ lọc tìm kiếm và xác nhận kết quả trả về khớp chính xác.
- **Automated Verification**:
  - Đảm bảo các chỉ số tính toán trong test suite (`tests/test_invoices.py`, `tests/test_analytics.py`) vẫn PASS 100% không bị ảnh hưởng bởi thay đổi giao diện.
