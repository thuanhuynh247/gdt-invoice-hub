# Khuym Context: Version 14.0.0 AI Tax Audit Simulation, Automated Transfer Pricing Compliance & Multi-Currency Treasury Management Hub

Quyết định thiết kế và phạm vi nghiệp vụ cho việc triển khai Phiên bản 14.0.0.

---

## 1. Phân loại & Phạm vi (Boundary & Domain)

* **Feature Slug**: `v14_roadmap`
* **Quy mô (Scope)**: `Deep` (Lộ trình chiến lược nâng cấp năng lực thanh tra thuế giả lập, tự động hóa hồ sơ giá giao dịch liên kết và hợp nhất ngân quỹ đa ngoại tệ sử dụng tỷ giá Vietcombank).
* **Phân loại Phân hệ (Domain Types)**:
  - `SEE`: Giao diện Dashboard giả lập thanh tra thuế, Offcanvas Drawer hiển thị khuyến nghị giải trình, Panel khai báo Giao dịch liên kết, Wizard lập Hồ sơ xác định giá, Dashboard đối chiếu đa ngoại tệ và bảng kê FCT.
  - `CALL`: Các API: `/api/audit/simulate`, `/api/audit/mitigation/letter`, `/api/transfer-pricing/transactions`, `/api/transfer-pricing/local-file`, `/api/treasury/exchange-rates`, `/api/fct/declarations`.
  - `RUN`: Công cụ tính điểm T-Score nâng cao, script thu thập và cập nhật tỷ giá VCB tự động hàng ngày, trình tạo báo cáo giải trình DOCX/PDF, công cụ tính FCT.
  - `ORGANIZE`: Bảng dữ liệu `AffiliatedPartner`, `ExchangeRate`, `FCTDeclaration`, `MitigationTemplate`, schema SQLite mở rộng.

---

## 2. Quyết định Đã khóa (Socratic Locked Decisions)

* **D1 [Mục tiêu Lộ trình v14]**: Triển khai giải pháp v14.0.0 bao gồm ba trụ cột: AI Tax Audit Simulation (Trình giả lập thanh tra thuế toàn diện và gợi ý giải trình pháp lý), Transfer Pricing Compliance (Nhận diện giao dịch liên kết và tự động hóa Hồ sơ quốc gia theo Nghị định 132/2020/NĐ-CP), và Multi-Currency Treasury & FCT (Hợp nhất đối chiếu ngoại tệ sử dụng tỷ giá VCB thực tế và kiểm toán thuế nhà thầu nước ngoài theo Thông tư 103/2014/TT-BTC).
* **D2 [Trọng số T-Score giả lập]**: Chỉ số rủi ro thuế (T-Score) sẽ được tính theo trọng số: Blacklisted MST (40%), Signature Delay (15%), Cash payment >= 20M (20%), Sequence gaps (10%), Template/Serial mismatch (15%). Điểm dưới 50 được đánh dấu High Risk.
* **D3 [Khung pháp lý Giao dịch liên kết]**: Nhận diện giao dịch liên kết dựa trên các tiêu chí Nghị định 132/2020/NĐ-CP (sở hữu chéo >= 25%, quan hệ điều hành chung, hoặc giao dịch chiếm trên 50% tổng giá trị mua vào/bán ra). EBITDA khống chế chi phí lãi vay ở mức 30%.
* **D4 [Tích hợp Tỷ giá VCB tự động]**: Bộ đối chiếu đa ngoại tệ (US-174) phải tích hợp trực tiếp với database tỷ giá VCB được cào hàng ngày từ Vietcombank. Trong trường hợp hóa đơn phát sinh vào ngày nghỉ, hệ thống sẽ sử dụng tỷ giá chuyển khoản của ngày làm việc liền trước gần nhất.
* **D5 [Quy tắc Gross-up / Net FCT]**: Bộ tính thuế FCT (US-175) hỗ trợ cả hai phương thức tính thuế: Net (doanh nghiệp Việt Nam chịu thuế thay, phải quy đổi doanh thu tính thuế trước) và Gross (nhà thầu nước ngoài chịu thuế, khấu trừ trực tiếp trên giá trị thanh toán).

---

## 3. Các Tệp Tin & Luồng Liên quan (Scout Paths)

* **Giao diện (SEE)**:
  - `templates/audit_dashboard.html` (Bảng điều khiển giả lập thanh tra thuế, phân tích T-Score)
  - `templates/transfer_pricing.html` (Khai báo liên kết, wizard xuất hồ sơ xác định giá)
  - `templates/treasury.html` (Đối chiếu ngoại tệ, bảng tỷ giá VCB và bảng tính FCT)
  - `static/js/audit_sim.js` (Gọi API mô phỏng, xuất công văn giải trình, tính toán FCT)
* **Nghiệp vụ (RUN / CALL / ORGANIZE)**:
  - `invoices/models.py` (Khai báo `AffiliatedPartner`, `ExchangeRate`, `FCTDeclaration`)
  - `invoices/audit_simulator.py` (Tính T-Score, kiểm tra 6 tiêu chí thanh tra thuế)
  - `invoices/mitigation_service.py` (Tra cứu văn bản pháp lý, tạo file DOCX giải trình mẫu)
  - `invoices/transfer_pricing.py` (Logic tính EBITDA, liên kết, xuất Appendix I)
  - `invoices/currency_reconciler.py` (Đối chiếu ngoại tệ VND-USD-EUR theo tỷ giá VCB)
  - `invoices/fct_auditor.py` (Tính thuế FCT VAT & CIT theo Thông tư 103)

---

## 4. Các Ý tưởng Tạm hoãn (Deferred Ideas)

* Tự động gửi hồ sơ giá chuyển nhượng trực tiếp lên cổng thông tin Thuế. (Hoãn lại, chỉ xuất file Word/Excel offline theo đúng mẫu pháp lý).
* Tự động cào tỷ giá từ các ngân hàng thương mại khác ngoài VCB (BIDV, Vietinbank). (Hoãn lại, VCB là nguồn tỷ giá chuẩn được chấp nhận rộng rãi nhất bởi GDT).
* Tích hợp AI sinh ngôn ngữ tự do hoàn toàn cho giải trình. (Hoãn lại, sử dụng template cấu trúc kết hợp điền thông tin tự động để đảm bảo tính chuẩn xác pháp lý cao nhất).
