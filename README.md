# 🚀 GDT Invoice Hub

> **Hệ thống Quản lý, Kiểm tra Rủi ro & Dự báo Thuế Hóa đơn Điện tử GTGT Việt Nam**  
> *An Intelligent VAT Invoice Management, Risk Assessment, and Predictive Tax Forecasting Platform for Vietnamese Businesses.*

---

## 🇻🇳 TIẾNG VIỆT

### 🌟 Tính Năng Nổi Bật
- **Quản lý Hóa đơn Điện tử**: Nhập khẩu và đồng bộ tệp XML hóa đơn điện tử GTGT chuẩn Tổng cục Thuế Việt Nam.
- **Kiểm tra Rủi ro T-Score**: Chấm điểm rủi ro người bán và hóa đơn tự động dựa trên 20+ tiêu chí kiểm thử nghiệm vụ nâng cao.
- **Trợ lý Thuế AI (Gemma-4 / Gemini / OpenAI)**:
  - Tự động nhận diện rủi ro, phân loại danh mục chi phí thông minh.
  - Tự soạn thảo **Công văn giải trình (Mitigation Letter)** gửi Cơ quan Thuế chuẩn chỉnh pháp lý theo Nghị định 30/2020/NĐ-CP và Thông tư 80/2021/TT-BTC.
- **Tự Phục Hồi Ngoại Tuyến (Offline Resilience)**: Tự động kích hoạt bộ sinh công văn cục bộ dựa trên luật định khi LLM mất kết nối.
- **Dự Báo Thuế GTGT Khấu Trừ (Predictive Tax Forecasting)**: Thuật toán ARIMA dự báo số thuế GTGT đầu vào/đầu ra và dòng tiền chịu thuế 3 tháng tiếp theo kèm theo vùng tin cậy sai số trực quan.
- **Xuất Bản Đa Định Dạng**: Hỗ trợ xuất file giải trình định dạng Word (.doc) và PDF chuyên nghiệp để in ấn.

### ⚙️ Hướng Dẫn Cài Đặt & Khởi Chạy
1. **Yêu cầu hệ thống**: Python 3.9+ (khuyên dùng Python 3.11)
2. **Cài đặt thư viện phụ thuộc**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Cấu hình môi trường**:
   Sao chép `.env.example` thành `.env` và cập nhật các cấu hình kết nối AI:
   ```bash
   copy .env.example .env
   ```
4. **Khởi chạy ứng dụng**:
   ```bash
   python run_local.py
   ```
   Sau đó truy cập địa chỉ: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🇬🇧 ENGLISH

### 🌟 Key Features
- **VAT XML Invoice Management**: Upload and visualize Vietnamese VAT XML invoices compliant with the General Department of Taxation (GDT).
- **Comprehensive T-Score Audit**: Audits seller and invoice legitimacy based on 20+ specialized risk indicators.
- **AI-Powered Tax Auditor & Chat**:
  - Automatically identifies tax anomalies, performs expense categorization.
  - Drafts highly professional legal mitigation letters (`Công văn giải trình`) in compliance with **Decree 30/2020/NĐ-CP** and **Circular 80/2021/TT-BTC**.
- **Offline-Resilience Fallback**: Automatically generates high-fidelity local legal explanation letters if LLMs are offline or disabled.
- **Predictive Tax Forecasting**: ARIMA-powered VAT forecasting for the next 3 months with historical variance margins and interactive visualization.
- **Multi-Format Export**: Instantly exports legal defense letters to MS Word (.doc) and PDF formats.

### ⚙️ Quick Start Guide
1. **Requirements**: Python 3.9+ (Python 3.11 recommended)
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
4. **Run Application**:
   ```bash
   python run_local.py
   ```
   Open your browser at: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.
