# 📋 KẾ HOẠCH KIỂM THỬ CHẤP NHẬN NGƯỜI DÙNG (UAT)
# GDT Invoice Hub — Enterprise Tax Analytics Platform v17.0.0

**Mã dự án**: INVOICE-WEBAPP-PLAN-A  
**Phiên bản**: v17.0.0  
**Ngày lập**: 2026-06-01  
**Trạng thái Quality Gate**: ✅ 448/449 tests PASSED (1 skipped E2E)

---

## 1. MỤC TIÊU UAT

| # | Mục tiêu | Tiêu chí đạt |
|---|----------|---------------|
| 1 | Xác nhận tất cả nghiệp vụ kế toán-thuế hoạt động đúng quy định pháp luật VN | 100% kịch bản nghiệp vụ PASS |
| 2 | Kiểm tra giao diện người dùng trên các trình duyệt phổ biến | Chrome, Edge, Firefox trên Windows |
| 3 | Xác nhận hiệu năng hệ thống đáp ứng yêu cầu thực tế | Thời gian phản hồi API ≤ 3 giây |
| 4 | Kiểm tra bảo mật nghiệp vụ và phân quyền truy cập | Không rò rỉ dữ liệu giữa các MST |
| 5 | Sẵn sàng bàn giao cho kế toán viên sử dụng hàng ngày | Hướng dẫn sử dụng hoàn chỉnh |

---

## 2. PHẠM VI KIỂM THỬ

### 2.1. Các module kiểm thử

| Module | Mô tả | Ưu tiên |
|--------|--------|---------|
| **AUTH** | Đăng nhập, phiên làm việc, RBAC | 🔴 Cao |
| **INVOICES** | Tra cứu, tải, import hóa đơn XML | 🔴 Cao |
| **T-SCORE** | Chấm điểm rủi ro thuế tự động | 🔴 Cao |
| **AI AUDITOR** | Kiểm toán AI, cảnh báo bất thường | 🟡 TB |
| **MULTI-MST** | Quản lý đa mã số thuế | 🔴 Cao |
| **CLOUD SYNC** | Đồng bộ Google Drive/OneDrive | 🟡 TB |
| **ERP EXPORT** | Xuất MISA/Odoo | 🟡 TB |
| **BCTC** | Biên dịch báo cáo tài chính | 🔴 Cao |
| **TAX PAYMENT** | Giấy nộp tiền + VietQR | 🔴 Cao |
| **E-COMMERCE** | Đồng bộ Shopee/TikTok | 🟡 TB |
| **BANK RECON** | Đối soát ngân hàng | 🔴 Cao |
| **CASHFLOW** | Dự báo dòng tiền | 🟢 Thấp |

### 2.2. Ngoài phạm vi
- Kiểm thử tải (Load Testing) — chưa yêu cầu ở giai đoạn này
- Kiểm thử bảo mật xâm nhập (Penetration Testing)
- Triển khai trên môi trường cloud (AWS/Azure)

---

## 3. MÔI TRƯỜNG KIỂM THỬ

### 3.1. Máy trạm UAT

| Thành phần | Yêu cầu |
|-----------|---------|
| **Hệ điều hành** | Windows 10/11 |
| **Python** | 3.10+ (đã cài sẵn trong `venv/`) |
| **Trình duyệt** | Chrome 120+, Edge 120+, Firefox 120+ |
| **Cổng mạng** | Port 5000 (localhost) |
| **Dung lượng đĩa** | ≥ 500MB trống |

### 3.2. Khởi chạy hệ thống

```powershell
# Bước 1: Mở PowerShell tại thư mục dự án
cd "d:\LearnAnyThing\Webapp XML"

# Bước 2: Kích hoạt môi trường ảo
.\venv\Scripts\activate

# Bước 3: Khởi chạy ứng dụng
python run_local.py

# Hệ thống tự động mở trình duyệt tại http://127.0.0.1:5000
```

### 3.3. Tài khoản kiểm thử

| Vai trò | Tài khoản | Mật khẩu | Quyền |
|---------|-----------|----------|-------|
| Admin | (GDT account) | (trong .env) | Toàn quyền |
| Kế toán viên | viewer_user | test123 | Xem, xuất báo cáo |
| Kiểm toán | auditor_user | test123 | Xem, kiểm toán, đối soát |

> **Lưu ý**: Ở chế độ Mock (`GDT_USE_MOCK=true`), hệ thống sử dụng dữ liệu mẫu, không cần kết nối thật tới cổng GDT.

---

## 4. KỊCH BẢN KIỂM THỬ CHI TIẾT

### 📌 TC-001: Đăng nhập & Quản lý Phiên

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Truy cập `http://127.0.0.1:5000` | Chuyển hướng tới trang đăng nhập |
| 2 | Nhập sai mật khẩu | Thông báo lỗi, không đăng nhập được |
| 3 | Nhập đúng thông tin | Chuyển hướng tới Dashboard hóa đơn |
| 4 | Đợi 31 phút không thao tác | Phiên hết hạn, yêu cầu đăng nhập lại |
| 5 | Truy cập `/api/invoices` khi chưa login | Trả về HTTP 401 |

### 📌 TC-002: Tra cứu & Tải Hóa đơn

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Chọn khoảng ngày và nhấn "Tra cứu" | Hiển thị danh sách hóa đơn đầu vào |
| 2 | Chuyển sang tab "Hóa đơn bán ra" | Hiển thị danh sách hóa đơn đầu ra |
| 3 | Nhấn nút tải XML cho 1 hóa đơn | Tải file .xml về máy |
| 4 | Nhấn "Tải hàng loạt" cho 1 tháng | Tải file .zip chứa tất cả XML |
| 5 | Nhấn "Xuất Excel" | Tải file .xlsx với đầy đủ cột dữ liệu |
| 6 | Nhấn "Xem PDF" cho 1 hóa đơn | Hiển thị hóa đơn dạng in ấn chuyên nghiệp |

### 📌 TC-003: Chấm điểm Rủi ro T-Score

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Xem cột T-Score trên danh sách hóa đơn | Hiển thị điểm 0-100 và rating (A++ đến F) |
| 2 | Hóa đơn MST nằm trong Blacklist | T-Score = 0, Rating = F, cảnh báo đỏ |
| 3 | Hóa đơn thanh toán tiền mặt > 20tr | T-Score bị trừ điểm, cảnh báo rủi ro |
| 4 | Hóa đơn chênh lệch thuế suất | Cảnh báo "Thuế suất không khớp" |

### 📌 TC-004: Kiểm toán AI (AI Auditor)

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Nhấn "Kiểm toán AI" cho 1 hóa đơn | Hiển thị kết quả phân tích AI |
| 2 | Xem chi tiết cảnh báo AI | Mô tả rõ lý do, mức độ rủi ro |
| 3 | Kiểm tra hóa đơn nghi ngờ gian lận | AI phát hiện và đánh dấu CRITICAL |

### 📌 TC-005: Quản lý Đa MST (Multi-MST)

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Tạo Profile MST mới qua API | Profile được lưu thành công |
| 2 | Chuyển đổi MST trên Navbar | Dữ liệu hóa đơn thay đổi theo MST mới |
| 3 | Xóa Profile MST | Profile bị xóa, dữ liệu vẫn giữ nguyên |
| 4 | Tra cứu hóa đơn với MST khác | Chỉ hiện hóa đơn của MST đã chọn |

### 📌 TC-006: Báo cáo Tài chính (BCTC)

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Truy cập trang "Thuế & BCTC" | Giao diện BCTC hiển thị đầy đủ |
| 2 | Nhập số dư tài khoản kế toán | Cân đối kế toán tự động tính toán |
| 3 | Nhấn "Biên dịch BCTC" | Sinh file XML chuẩn HTKK |
| 4 | Cân đối kế toán không cân | Cảnh báo "Bảng CĐKT mất cân đối" |
| 5 | Kiểm toán sổ cái | Phát hiện chênh lệch sổ cái vs hóa đơn |

### 📌 TC-007: Giấy nộp tiền & VietQR

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Chọn loại thuế (GTGT/TNDN/TNCN) | Form hiện mã chương + tiểu mục đúng |
| 2 | Nhập số tiền nộp thuế | Tự sinh Giấy nộp tiền XML Mẫu 711/MB |
| 3 | Tạo mã VietQR | Hiển thị mã QR có thể quét bằng app ngân hàng |
| 4 | Kiểm tra CRC16 trong chuỗi QR | Khớp chuẩn EMVCo (test_crc16_compliance) |

### 📌 TC-008: Đối soát Ngân hàng

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Upload file CSV sổ phụ ngân hàng | Phân tích cú pháp thành công |
| 2 | Chạy đối soát tự động | Khớp giao dịch ngân hàng với hóa đơn |
| 3 | Hóa đơn > 20tr thanh toán tiền mặt | Cảnh báo vi phạm quy định GTGT |
| 4 | Giao dịch ngân hàng không khớp hóa đơn | Đánh dấu "Chờ xác minh" |

### 📌 TC-009: Đồng bộ Sàn TMĐT

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Đồng bộ đơn hàng Shopee | Tạo hóa đơn bán tổng hợp + hóa đơn phí sàn |
| 2 | Đối soát doanh thu vs hóa đơn GDT | Phát hiện khoản doanh thu chưa xuất hóa đơn |
| 3 | Kiểm tra Risk Score | Điểm rủi ro ẩn thuế phản ánh chính xác |

### 📌 TC-010: Xuất ERP (MISA/Odoo)

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Xuất file MISA Excel | File Excel có đúng format MISA SME |
| 2 | Xuất file Odoo CSV | File CSV có đúng cấu trúc bút toán kép |
| 3 | Import file vào MISA thử | Không lỗi parse (nếu có bản MISA) |

### 📌 TC-011: Chatbot Trợ lý AI

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Hỏi "Tổng chi mua hàng tháng 5?" | Chatbot trả lời số liệu chính xác |
| 2 | Hỏi "Luật thuế GTGT nói gì về hoàn thuế?" | Chatbot trích dẫn từ luật 48/2024 |
| 3 | Hỏi câu SQL injection | Chatbot từ chối, không thực thi |

### 📌 TC-012: Dự báo Dòng tiền

| Bước | Hành động | Kết quả mong đợi |
|------|-----------|-------------------|
| 1 | Truy cập Dashboard Cashflow | Biểu đồ hiện phải thu/phải trả |
| 2 | Chạy mô phỏng "What-if" | Kết quả thay đổi theo tham số |
| 3 | Phân tích tuổi nợ (Aging Buckets) | Nhóm nợ 0-30, 31-60, 61-90, >90 ngày |

---

## 5. TIÊU CHÍ ĐẠT/KHÔNG ĐẠT

### 5.1. Tiêu chí ĐẠT (Go)
- ✅ 100% kịch bản ưu tiên 🔴 Cao đều PASS
- ✅ ≥ 90% kịch bản ưu tiên 🟡 Trung bình đều PASS  
- ✅ Không có lỗi nghiêm trọng (Blocker/Critical) chưa sửa
- ✅ Hiệu năng API phản hồi ≤ 3 giây trên máy trạm cục bộ
- ✅ Dữ liệu không bị rò rỉ giữa các MST

### 5.2. Tiêu chí KHÔNG ĐẠT (No-Go)
- ❌ Có lỗi Blocker ảnh hưởng đến nghiệp vụ kế toán
- ❌ Sai sót trong tính toán thuế (BCTC mất cân đối, VAT sai)
- ❌ Rò rỉ dữ liệu giữa các tài khoản MST
- ❌ Ứng dụng crash khi xử lý dữ liệu thực tế

---

## 6. LỊCH TRÌNH UAT

| Ngày | Hoạt động | Người thực hiện |
|------|-----------|-----------------|
| Ngày 1 | Cài đặt môi trường, chạy TC-001, TC-002 | Nhóm QA |
| Ngày 2 | Chạy TC-003, TC-004, TC-005 | Nhóm QA + Kế toán |
| Ngày 3 | Chạy TC-006, TC-007, TC-008 | Kế toán trưởng |
| Ngày 4 | Chạy TC-009, TC-010, TC-011, TC-012 | Nhóm QA |
| Ngày 5 | Tổng hợp kết quả, sửa lỗi (nếu có) | Dev + QA |
| Ngày 6 | Kiểm thử hồi quy sau sửa lỗi | Nhóm QA |
| Ngày 7 | Ký biên bản nghiệm thu UAT | Ban lãnh đạo |

---

## 7. BIÊN BẢN NGHIỆM THU (MẪU)

```
BIÊN BẢN NGHIỆM THU KIỂM THỬ CHẤP NHẬN NGƯỜI DÙNG (UAT)
Dự án: GDT Invoice Hub v17.0.0
Ngày: ____/____/2026

Kết quả:
  - Tổng số kịch bản: 12
  - Kịch bản ĐẠT: ____
  - Kịch bản KHÔNG ĐẠT: ____
  - Kịch bản hoãn: ____

Kết luận: ĐẠT / KHÔNG ĐẠT

Ký tên:
  Trưởng nhóm QA: __________________
  Kế toán trưởng: __________________
  Giám đốc phê duyệt: __________________
```

---

## 8. HƯỚNG DẪN BÁO CÁO LỖI

Khi phát hiện lỗi trong quá trình UAT, ghi nhận theo mẫu:

| Trường | Nội dung |
|--------|---------|
| **Mã lỗi** | UAT-XXX |
| **Mức độ** | Blocker / Critical / Major / Minor |
| **Kịch bản** | TC-00X, Bước Y |
| **Mô tả** | Mô tả chi tiết lỗi |
| **Bước tái hiện** | 1. ... 2. ... 3. ... |
| **Kết quả thực tế** | Mô tả những gì xảy ra |
| **Kết quả mong đợi** | Mô tả những gì đáng lẽ phải xảy ra |
| **Ảnh chụp màn hình** | Đính kèm (nếu có) |
| **Trình duyệt** | Chrome 120 / Edge 120 / Firefox 120 |
