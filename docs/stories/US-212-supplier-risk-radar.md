# Story Specification: US-212 — AI-Powered GDT Supplier Risk Radar & Shell Company Detector

## 📋 Context & Business Value
Đối với doanh nghiệp, việc giao dịch với các nhà cung cấp có rủi ro cao hoặc các công ty "ma" (mua bán hóa đơn khống rồi bỏ trốn) là mối đe dọa cực kỳ nghiêm trọng về mặt pháp lý và thuế (bị loại chi phí hợp lý, loại thuế GTGT đầu vào và phạt nặng). 
Để chủ động bảo vệ doanh nghiệp, chúng ta cần một hệ thống **Cảnh báo Sớm & Đánh giá Tín nhiệm người bán tự động bằng AI (GDT Supplier Risk Radar)**. Hệ thống này tính toán điểm số tín nhiệm rủi ro (0-100) và xếp hạng tín nhiệm (A++ đến F) của từng nhà cung cấp dựa trên dữ liệu hóa đơn trong hệ thống, trạng thái thuế GDT thực tế và các hành vi bất thường.

---

## 🎯 Acceptance Criteria

### 1. Dynamic Supplier Risk Engine (`invoices/supplier_risk_service.py`)
Xây dựng một service chuyên biệt để tính toán điểm rủi ro:
- **Baseline Score**: Khởi điểm từ 100 điểm.
- **Trạng thái Thuế GDT**:
  - `Đang hoạt động (đã được cấp MST)`: -0 điểm.
  - `Tạm ngừng hoạt động`: -25 điểm.
  - `Ngừng hoạt động, đã đóng MST`: -50 điểm.
  - `Mã số thuế không tồn tại`: -75 điểm.
  - `BLACKLIST`: Nếu MST của nhà cung cấp nằm trong bảng `BlacklistedMST`, điểm số lập tức giảm về **0** (Rating **F**).
- **Đột biến Sản lượng / Tần suất (Invoice Volume Velocity Spike)**:
  - Nếu tổng tiền hóa đơn trong một tháng dương lịch bất kỳ vượt quá **300%** so với trung bình tháng lịch sử của nhà cung cấp đó (chỉ xét nhà cung cấp có lịch sử từ 3 tháng trở lên), khấu trừ **20 điểm**.
  - Nếu là nhà cung cấp mới hoàn toàn (lịch sử < 3 tháng) nhưng phát sinh tổng doanh số > **500,000,000 VND** trong tháng đầu tiên, khấu trừ **20 điểm**.
- **Tỷ lệ Chữ ký số Ký muộn (Late Digital Signing Ratio)**:
  - Một hóa đơn được coi là ký muộn nếu ngày ký chữ ký số trễ hơn ngày lập hóa đơn > **3 ngày**.
  - Nếu tỷ lệ hóa đơn ký muộn trên tổng số hóa đơn của NCC này > **20%**, khấu trừ **15 điểm**.
- **Rủi ro Chia nhỏ Hóa đơn tránh Ngưỡng tiền mặt (Cash-Threshold Splitting Evasion)**:
  - Hóa đơn mua hàng từ 20 triệu VND trở lên bắt buộc thanh toán không dùng tiền mặt để được khấu trừ VAT. Nhiều doanh nghiệp lách luật bằng cách chia nhỏ hóa đơn dưới 20 triệu (ví dụ từ 19,000,000 đến 19,999,999 VND) và thanh toán tiền mặt.
  - Nếu NCC có từ **2 hóa đơn trở lên** trong cùng một tháng dùng phương thức thanh toán tiền mặt với số tiền mỗi hóa đơn nằm trong khoảng `[19,000,000 - 19,999,999]` VND, khấu trừ **15 điểm**.
- **Phân tích AI từ khóa Nội dung hàng hóa Suspicious (Suspicious Text Signature)**:
  - Phân tích tên sản phẩm/dịch vụ trên các dòng chi tiết hóa đơn (line items).
  - Nếu phát hiện các từ khóa rủi ro cao về trốn thuế/hóa đơn ảo như: `"dịch vụ tư vấn"`, `"tư vấn quản lý"`, `"chi phí hỗ trợ"`, `"dịch vụ tiếp khách"`, `"dịch vụ ăn uống"`, `"quảng cáo không rõ nội dung"`, `"khảo sát thị trường"` và có giá trị trung bình hóa đơn > **50,000,000 VND**, khấu trừ **15 điểm**.

### 2. Xếp hạng Tín nhiệm (Trust Rating Scale)
- Điểm từ 95 - 100: **A++** (Độ tin cậy tuyệt đối)
- Điểm từ 85 - 94: **A** (Độ tin cậy cao)
- Điểm từ 70 - 84: **B** (Độ tin cậy trung bình)
- Điểm từ 50 - 69: **C** (Rủi ro thấp)
- Điểm từ 30 - 49: **D** (Rủi ro trung bình)
- Điểm dưới 30 hoặc Blacklisted: **F** (Nguy hiểm cực kỳ - Bỏ trốn / Khống)

### 3. Cung cấp API Endpoints (`invoices/routes.py`)
- `GET /api/reports/supplier-risk-radar`:
  - Trích xuất dữ liệu của tất cả nhà cung cấp có giao dịch với doanh nghiệp hiện tại.
  - Tính toán điểm rủi ro, phân loại cảnh báo vi phạm.
  - Trả về thống kê tổng hợp và danh sách nhà cung cấp phân loại chi tiết.
- `POST /api/reports/supplier-risk-radar/blacklist`:
  - Thêm một nhà cung cấp mới vào danh sách đen `BlacklistedMST` (giảm điểm tín nhiệm về 0 ngay lập tức).

### 4. Giao diện trực quan trong Dashboard BCTC (`templates/tax_bctc.html`)
- Thay thế hoặc tích hợp API mới vào Tab 6 (Bảng điểm Rủi ro Thuế) để tải và hiển thị danh sách NCC rủi ro theo thang điểm tín nhiệm A++ tới F cực kỳ trực quan, có màu sắc đồng bộ hoàn hảo theo Wise Fintech Aesthetic.

---

## 🛠️ Verification & Test Plan

- **Unit & Integration Tests (`tests/test_supplier_risk.py`)**:
  - Test thuật toán tính điểm rủi ro cho từng kịch bản (Blacklist, Volume Spike, Late Signing, Cash Splitting, Suspicious Keywords).
  - Test API endpoint `/api/reports/supplier-risk-radar`.
  - Đảm bảo 100% test case trong suite vượt qua thành công.
