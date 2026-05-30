# Feasibility Validation: Version 14.0.0 AI Tax Audit Simulation, Automated Transfer Pricing Compliance & Multi-Currency Treasury Management Hub

Báo cáo kết quả kiểm chứng tính khả thi kỹ thuật và ma trận sẵn sàng triển khai cho Version 14.0.0.

---

## 1. Ma trận Khả thi (Feasibility Matrix)

| Phân hệ / Tính năng | Tính khả thi | Phương án chứng minh | Mức độ rủi ro | Trạng thái sẵn sàng |
|---|---|---|---|---|
| **Tax Audit Simulator** | **100%** | Kết hợp các kiểm tra hiện có (MST, signing date, non-cash check) vào một scoring engine có trọng số. | Thấp | **READY** |
| **Audit Mitigation Adviser** | **100%** | Định cấu hình bản đồ ánh xạ mã lỗi → điều khoản luật. Sinh file `.docx` mẫu bằng `python-docx` / sinh PDF bằng `reportlab`. | Thấp | **READY** |
| **Related Party Transaction Detector** | **95%** | Lọc dữ liệu mua bán từ các đối tác được cấu hình thuộc nhóm liên kết. Tính toán tỷ lệ EBITDA dựa trên báo cáo kết quả kinh doanh. | Thấp | **READY** |
| **TP Local File Scaffolder** | **90%** | Tạo wizard thu thập thông tin doanh nghiệp, tự động tổng hợp bảng biểu giao dịch và điền vào form mẫu Word. | Trung bình | **READY** |
| **Multi-Currency Treasury Reconciler** | **100%** | Sử dụng database tỷ giá VCB hiện có từ tool cào tỷ giá. Áp dụng thuật toán chọn tỷ giá ngày liền trước cho ngày nghỉ. | Thấp | **READY** |
| **FCT Compliance Auditor** | **100%** | Áp dụng công thức tính FCT cho Gross/Net contract từ metadata hóa đơn của nhà cung cấp nước ngoài. | Thấp | **READY** |

---

## 2. Kế hoạch Kiểm thử & Hậu nghiệm (Verification Strategy)

1. **Kiểm thử Tax Audit Simulator (`tests/test_v14_audit_simulator.py`)**:
   - Giả lập cơ sở dữ liệu hóa đơn với các lỗi vi phạm khác nhau (ký muộn, MST đen, thanh toán tiền mặt lớn).
   - Xác minh T-Score được tính toán chính xác theo đúng bảng trọng số thiết kế.
   - Kiểm tra API trả về đúng phân loại cảnh báo (Low, Medium, High).

2. **Kiểm thử Mitigation Adviser (`tests/test_v14_mitigation_adviser.py`)**:
   - Chạy giả lập và kích hoạt cảnh báo ký muộn.
   - Xác minh đề xuất chứa đúng trích dẫn Nghị định 125/2020/NĐ-CP.
   - Kích hoạt API xuất thư giải trình và kiểm tra nội dung file DOCX đầu ra chứa MST và số hóa đơn bị cảnh báo.

3. **Kiểm thử Related Party Detector (`tests/test_v14_tp_detector.py`)**:
   - Tạo đối tác có cấu hình affiliated. Ghi nhận giao dịch mua bán.
   - Xác minh công cụ tính toán tổng giá trị liên kết và hiển thị cảnh báo giới hạn EBITDA chi phí lãi vay khi vượt ngưỡng.

4. **Kiểm thử TP Local File Scaffolder (`tests/test_v14_tp_scaffolder.py`)**:
   - Chạy wizard xuất hồ sơ quốc gia với dữ liệu mẫu.
   - Xác minh file Word sinh ra có cấu trúc các chương đầy đủ và bảng Appendix I khớp số liệu tổng hợp giao dịch liên kết.

5. **Kiểm thử Multi-Currency Reconciler (`tests/test_v14_currency_reconciler.py`)**:
   - Import hóa đơn USD vào ngày chủ nhật.
   - Xác minh hệ thống tự động tra cứu tỷ giá VCB ngày thứ sáu liền trước để quy đổi sang VND.
   - Kiểm tra tính đúng đắn của việc quy đổi theo tỷ giá Mua (phải thu) và Bán (phải trả).

6. **Kiểm thử FCT Compliance Auditor (`tests/test_v14_fct_auditor.py`)**:
   - Chạy kiểm toán hóa đơn Meta Ads (Net contract) và AWS (Gross contract).
   - Xác minh số thuế FCT VAT và FCT CIT khấu trừ tương ứng khớp với thuật toán trích từ Thông tư 103.
   - Kiểm tra xuất bảng kê FCT sang Excel.
