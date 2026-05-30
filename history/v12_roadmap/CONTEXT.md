# Khuym Context: Version 12.0.0 Smart Cash Flow Forecasting, AI Tax Optimization & Cross-Tenant Consolidated Analytics

Quyết định thiết kế và phạm vi nghiệp vụ cho việc triển khai Phiên bản 12.0.0.

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `v12_roadmap`
* **Quy mô (Scope)**: `Deep` (Lộ trình nghiệp vụ tích hợp mô phỏng dòng tiền, kiểm toán thuế TNDN doanh nghiệp, và hợp nhất dữ liệu đa MST).
* **Phân loại Phân hệ (Domain Types)**:
  - `SEE`: Giao diện Mô phỏng Scenario Simulator, Bảng khuyến nghị CIT Deduction Advisory, Dashboard hợp nhất Cross-Tenant Consolidated UI.
  - `CALL`: Các API: `/api/finance/cashflow`, `/api/tax/cit-audit`, `/api/tenant/consolidated`.
  - `RUN`: Các tiến trình tính toán dòng tiền rolling và phân loại cảnh báo khấu hao tài sản cố định.
  - `ORGANIZE`: Cấu trúc mô hình dữ liệu nhóm tài khoản liên MST, định dạng báo cáo slide PowerPoint/PDF tóm tắt quản trị.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu Lộ trình v12]**: Triển khai gói giải pháp Doanh nghiệp v12.0.0 tích hợp ba trụ cột: Dự báo dòng tiền thông minh và mô phỏng stress-test (Smart Cash Flow & Scenario Simulator), Trợ lý kiểm toán và tối ưu hóa thuế TNDN (AI CIT Tax Optimization & Deduction Advisory), và Dashboard hợp nhất báo cáo liên công ty (Cross-Tenant Consolidated Dashboard & Slide Exporter).
* **D2 [Ràng buộc CIT Nghiệp vụ]**: Tích hợp các luật kiểm tra cứng cho chi phí không được trừ theo luật Thuế TNDN Việt Nam (Thông tư 96/2015/TT-BTC):
  - Hóa đơn mua hàng từ 20 triệu VND trở lên không có chứng từ thanh toán không dùng tiền mặt.
  - Chi phí khấu hao xe ô tô dưới 9 chỗ ngồi có giá trị vượt trên 1,6 tỷ VND.
  - Hóa đơn từ các MST bị khóa/bỏ trốn.
* **D3 [Bảo mật Đa Khách thuê Hợp nhất]**: Dashboard hợp nhất (Consolidated View) chỉ cho phép truy cập bởi tài khoản thuộc nhóm Quản trị Tập đoàn (Group Admin) được gán quyền rõ ràng trong database.
* **D4 [Thiết kế Mô phỏng Không Lưu trạng thái (Stateless Simulation)]**: Trình mô phỏng Scenario Simulator sẽ xử lý tính toán động phía Client/API stateless, không thay đổi trực tiếp trạng thái hóa đơn thực tế trong database trừ khi người dùng xác nhận ghi đè kỳ hạn thanh toán mới.

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  - `templates/base.html` (Thêm menu Dự báo dòng tiền & Kiểm toán TNDN & Dashboard tập đoàn)
  - `templates/dashboard.html` (Thêm widget cashflow và cảnh báo thuế CIT)
  - `static/js/main.js` (Điều phối gọi API cashflow, render đồ thị mô phỏng dòng tiền)
* **Nghiệp vụ (RUN / CALL / ORGANIZE)**:
  - `invoices/models.py` (Khai báo mối liên kết group_tenant và phân quyền liên MST)
  - `invoices/routes.py` (Đăng ký endpoint `/api/finance/cashflow`, `/api/tax/cit-audit`, v.v.)
  - `invoices/service.py` (Thuật toán tính toán dòng tiền rolling và luật lọc chi phí CIT)
  - `export/service.py` (Sinh file PowerPoint/PDF tóm tắt quản trị tập đoàn)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)

* Tự động đồng bộ dòng tiền với các phần mềm ERP ngoài (SAP/Oracle via API). (Hoãn lại, sử dụng mô hình dự báo nội bộ từ hóa đơn Hub).
* Sử dụng AI LLM tự động viết slide thuyết trình chi tiết. (Hoãn lại, sử dụng template Slide có cấu trúc sẵn và điền số liệu thống kê thực tế để đảm bảo độ chính xác tài chính).
