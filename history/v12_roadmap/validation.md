# Feasibility Validation: Version 12.0.0 Smart Cash Flow Forecasting, AI Tax Optimization & Cross-Tenant Consolidated Analytics

Báo cáo kết quả kiểm chứng tính khả thi kỹ thuật, dữ liệu thực nghiệm và ma trận sẵn sàng triển khai cho Version 12.0.0.

---

## 1. Ma trận Khả thi (Feasibility Matrix)

| Phân hệ / Tính năng | Tính khả thi | Phương án chứng minh | Mức độ rủi ro | Trạng thái sẵn sàng |
|---|---|---|---|---|
| **Smart Cash Flow Predictor** | **100%** | Kết hợp dữ liệu ngày thanh toán thực tế (hoặc ngày phát hành + kỳ hạn thanh toán mặc định) với số dư ban đầu để vẽ đường xu hướng tiền mặt. | Thấp | **READY** |
| **Scenario Simulator** | **100%** | Xây dựng API tính toán nhanh nhận các tham số đầu vào (tỉ lệ trễ thanh toán, tỉ lệ từ chối hóa đơn) và trả về mảng dữ liệu dự báo để UI hiển thị. | Thấp | **READY** |
| **CIT Deduction Auditor Engine** | **100%** | Thiết kế tập luật cứng phân tích thuộc tính hóa đơn và so khớp chi tiết mặt hàng bằng NLP/Regex nhằm phát hiện tài sản vượt định mức hoặc hóa đơn tiền mặt quá hạn. | Thấp | **READY** |
| **Deduction Advisory Panel** | **100%** | Xây dựng cơ sở tri thức thuế TNDN và gợi ý các hành động khắc phục cụ thể theo cấu trúc quy chuẩn. | Thấp | **READY** |
| **Cross-Tenant Consolidated UI** | **100%** | Truy vấn động gộp dữ liệu từ các tệp tin CSDL SQLite tenant của các doanh nghiệp thành viên liên kết và hiển thị tổng quan. | Trung bình (cần đảm bảo cô lập dữ liệu chuẩn) | **READY** |
| **Consolidated Slide Exporter** | **100%** | Dùng thư viện python-pptx sinh slide mẫu hoặc cấu trúc PDF bảng biểu định dạng chuyên nghiệp. | Thấp | **READY** |

---

## 2. Kế hoạch Kiểm thử & Hậu nghiệm (Verification Strategy)

Khi bước vào giai đoạn thực thi (Execution), chúng tôi sẽ triển khai các bộ test tự động sau:
1. **Kiểm thử Cash Flow & Simulation (`tests/test_v12_cashflow.py`)**:
   - Xác minh thuật toán tính dòng tiền lũy kế rolling chính xác dựa trên danh sách hóa đơn đầu vào/đầu ra giả lập.
   - Xác minh API simulator trả về số liệu chính xác khi điều chỉnh độ trễ thanh toán.
2. **Kiểm thử CIT Auditor Engine (`tests/test_v12_cit_audit.py`)**:
   - Gửi hóa đơn mua xe ô tô trị giá 2 tỷ VND và hóa đơn mua hàng thanh toán tiền mặt 25 triệu VND.
   - Xác minh engine gắn cờ cảnh báo không được khấu trừ thuế TNDN tương ứng.
3. **Kiểm thử Cross-Tenant Consolidated View (`tests/test_v12_consolidated.py`)**:
   - Giả lập 2 tenant khác nhau chứa hóa đơn thực tế.
   - Truy vấn API báo cáo hợp nhất và kiểm tra tổng doanh thu, VAT đầu vào/đầu ra có khớp với tổng của 2 tenant thành phần.
4. **Kiểm thử Slide Exporter (`tests/test_v12_slide_exporter.py`)**:
   - Xuất tệp PowerPoint/PDF và kiểm tra tính toàn vẹn của tệp xuất ra.
