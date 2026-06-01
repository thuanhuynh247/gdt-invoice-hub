# 📘 HƯỚNG DẪN SỬ DỤNG — GDT Invoice Hub v17.0.0
# Dành cho Kế toán viên & Nhân viên Tài chính

---

## 🚀 1. KHỞI CHẠY ỨNG DỤNG

### Cách 1: Chạy nhanh (khuyến nghị)
1. Mở **PowerShell** hoặc **Command Prompt**
2. Di chuyển tới thư mục dự án:
   ```
   cd "d:\LearnAnyThing\Webapp XML"
   ```
3. Chạy lệnh:
   ```
   venv\Scripts\python run_local.py
   ```
4. Trình duyệt tự động mở tại địa chỉ: **http://127.0.0.1:5000**

### Cách 2: Docker (cho IT)
```bash
docker-compose up -d
# Truy cập: http://localhost:5000
```

### Dừng hệ thống
- Nhấn **Ctrl + C** trong cửa sổ PowerShell đang chạy

---

## 🔐 2. ĐĂNG NHẬP

1. Nhập **Mã số thuế (MST)** và **Mật khẩu** tài khoản trên cổng `hoadondientu.gdt.gov.vn`
2. Hệ thống tự động giải mã Captcha (nếu có)
3. Sau khi đăng nhập thành công → Chuyển đến **Dashboard hóa đơn**

> ⚠️ Phiên làm việc hết hạn sau **30 phút** không thao tác. Cần đăng nhập lại.

---

## 📄 3. TRA CỨU HÓA ĐƠN

### 3.1. Tìm kiếm
1. Chọn **Ngày bắt đầu** và **Ngày kết thúc**
2. Chọn loại: **Hóa đơn mua vào** hoặc **Hóa đơn bán ra**
3. Nhấn **🔍 Tra cứu**

### 3.2. Xem chi tiết
- Nhấn vào hóa đơn bất kỳ → Xem chi tiết dòng hàng, thuế suất, tổng tiền

### 3.3. Tải hóa đơn
| Nút | Chức năng |
|-----|-----------|
| 📥 Tải XML | Tải file XML gốc của 1 hóa đơn |
| 📦 Tải hàng loạt | Tải tất cả hóa đơn trong tháng → file ZIP |
| 📊 Xuất Excel | Xuất danh sách hóa đơn ra file Excel |
| 🖨️ Xem PDF | Xem hóa đơn dạng in ấn chuyên nghiệp |

---

## 🏢 4. QUẢN LÝ ĐA DOANH NGHIỆP (Multi-MST)

1. Nhấn vào **dropdown MST** trên thanh điều hướng (Navbar)
2. Chọn MST doanh nghiệp cần quản lý
3. Toàn bộ dữ liệu (hóa đơn, báo cáo, kiểm toán) tự động chuyển sang MST mới

### Thêm MST mới
- Vào **Cài đặt** → **Quản lý Profile MST** → **Thêm mới**
- Nhập: MST, Tên công ty, Thông tin đăng nhập GDT

---

## 🛡️ 5. CHẤM ĐIỂM RỦI RO THUẾ (T-Score)

Mỗi hóa đơn được hệ thống AI tự động chấm điểm **T-Score** từ 0 đến 100:

| Xếp hạng | Điểm | Ý nghĩa |
|-----------|-------|---------|
| 🟢 A++ | 90-100 | Hoàn toàn an toàn |
| 🟢 A+ | 80-89 | Rủi ro rất thấp |
| 🟡 B | 60-79 | Cần kiểm tra thêm |
| 🟠 C | 40-59 | Rủi ro đáng chú ý |
| 🔴 D | 20-39 | Rủi ro cao |
| ⛔ F | 0-19 | Nghi ngờ gian lận — CẦN XỬ LÝ NGAY |

### Các yếu tố trừ điểm:
- MST nhà cung cấp nằm trong **Danh sách đen** của GDT
- Thanh toán **tiền mặt > 20 triệu VND** (vi phạm Luật Thuế GTGT)
- Chênh lệch **thuế suất** giữa dòng hàng và tổng
- Chữ ký số **hết hạn** hoặc bị **giả mạo**

---

## 📊 6. BÁO CÁO TÀI CHÍNH (BCTC)

### Truy cập: Menu → **Thuế & BCTC**

### 6.1. Biên dịch BCTC
1. Nhập **số dư đầu kỳ/cuối kỳ** cho các tài khoản kế toán (111, 112, 131, 331...)
2. Nhấn **Biên dịch BCTC**
3. Hệ thống sinh:
   - **Bảng cân đối kế toán (B01-DN)**
   - **Báo cáo kết quả kinh doanh (B02-DN)**
   - **Báo cáo lưu chuyển tiền tệ (B03-DN)**
4. Tải file **XML chuẩn HTKK** để nhập vào phần mềm kê khai thuế

### 6.2. Kiểm toán sổ cái
- Nhấn **Kiểm toán sổ cái** → So sánh số liệu sổ cái với hóa đơn điện tử
- Phát hiện: Hóa đơn thiếu bút toán, bút toán thiếu hóa đơn

---

## 💳 7. GIẤY NỘP TIỀN & VIETQR

### Truy cập: Tab **Giấy nộp tiền** trong trang Thuế & BCTC

1. Chọn **Loại thuế**: GTGT, TNDN, hoặc TNCN
2. Nhập **Số tiền nộp**
3. Chọn **Chương/Loại doanh nghiệp** (Doanh nghiệp tư nhân, TNHH, Cổ phần...)
4. Nhấn **Tạo Giấy nộp tiền**

**Kết quả:**
- File XML Mẫu 711/MB (Giấy nộp tiền vào NSNN)
- **Mã VietQR** — Quét bằng ứng dụng ngân hàng (Vietcombank, BIDV, Techcombank...) để nộp thuế tức thời

---

## 🏦 8. ĐỐI SOÁT NGÂN HÀNG

### Truy cập: Tab **Đối soát NH** trong trang chính

1. **Upload file CSV** sổ phụ ngân hàng (định dạng: Ngày, Số tiền, Nội dung, Số tham chiếu)
2. Nhấn **Chạy đối soát tự động**
3. Kết quả:
   - ✅ **Khớp** — Giao dịch NH khớp với hóa đơn
   - ⚠️ **Chờ xác minh** — Hóa đơn CK nhưng chưa tìm thấy giao dịch NH
   - ❌ **Vi phạm** — Hóa đơn > 20tr thanh toán tiền mặt

---

## 🛍️ 9. ĐỒNG BỘ SÀN TMĐT

### Truy cập: Tab **TMĐT** trong trang Thuế & BCTC

1. Chọn sàn: **Shopee**, **Lazada**, hoặc **TikTok Shop**
2. Nhập hoặc upload danh sách đơn hàng
3. Nhấn **Đồng bộ** → Hệ thống tự tạo:
   - Hóa đơn bán hàng tổng hợp theo ngày
   - Hóa đơn phí dịch vụ sàn (Commission + Service Fee)
4. Nhấn **Đối soát** → So sánh doanh số sàn với hóa đơn GDT

---

## 📤 10. XUẤT DỮ LIỆU ERP

| Phần mềm | Định dạng | Cách xuất |
|-----------|-----------|-----------|
| **MISA SME** | Excel (.xlsx) | Menu → Xuất ERP → MISA |
| **Odoo** | CSV | Menu → Xuất ERP → Odoo |

File xuất có thể import trực tiếp vào phần mềm kế toán tương ứng.

---

## 🤖 11. TRỢ LÝ AI (Chatbot)

### Truy cập: Tab **Trợ lý AI** trên trang hóa đơn chính

Hỏi bằng **tiếng Việt tự nhiên**, ví dụ:
- "Tổng chi mua hàng tháng 5 là bao nhiêu?"
- "Liệt kê hóa đơn có T-Score dưới 50"
- "Luật thuế GTGT nói gì về điều kiện hoàn thuế?"
- "Cho tôi danh sách nhà cung cấp có rủi ro cao"

> 💡 AI sử dụng dữ liệu hóa đơn thực tế trong hệ thống + Luật thuế 48/2024 và 149/2024 để trả lời chính xác.

---

## 💰 12. DỰ BÁO DÒNG TIỀN

### Truy cập: Menu → **Cashflow Oracle**

- **Biểu đồ phải thu/phải trả** — Theo thời gian
- **Phân tích tuổi nợ** — Nhóm: 0-30 ngày, 31-60, 61-90, >90 ngày
- **Mô phỏng What-If** — Thử các kịch bản "chậm thanh toán" để đánh giá tác động

---

## ❓ CÂU HỎI THƯỜNG GẶP

### Q: Dữ liệu có bị mất khi tắt ứng dụng?
**A:** Không. Toàn bộ dữ liệu được lưu trong file SQLite tại `data/invoices.db`. Chỉ cần khởi chạy lại là dữ liệu vẫn nguyên vẹn.

### Q: Có cần kết nối Internet không?
**A:** Cần kết nối Internet để tra cứu hóa đơn từ cổng GDT. Tuy nhiên, dữ liệu đã tải về có thể xem offline.

### Q: Làm sao để sao lưu dữ liệu?
**A:** Copy toàn bộ thư mục `data/` ra ổ USB hoặc Cloud. Hoặc sử dụng tính năng **Đồng bộ Cloud** (Google Drive / OneDrive) trong Cài đặt.

### Q: Tôi gặp lỗi "500 Internal Server Error"?
**A:** Thử:
1. Tắt và khởi chạy lại ứng dụng
2. Kiểm tra file `.env` có đầy đủ thông tin
3. Liên hệ bộ phận IT với nội dung lỗi chi tiết trong cửa sổ console

### Q: T-Score của hóa đơn bị 0 nhưng hóa đơn hợp lệ?
**A:** Kiểm tra xem MST nhà cung cấp có nằm trong Danh sách đen GDT không. Nếu đây là kết quả sai, vào **Cài đặt → Blacklist** để gỡ bỏ.
