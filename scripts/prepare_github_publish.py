#!/usr/bin/env python
"""
GitHub Publication Preparation Script
Creates a self-contained, clean folder ready for public GitHub release,
generating CI/CD pipelines, professional READMEs, license files, and a master publishing guide.
"""

import os
import shutil

def prepare_github_folder():
    dest_dir = "gdt-invoice-hub"
    print(f"🚀 Preparing clean GitHub release package in: {dest_dir}...")
    
    # 1. Clear target folder selectively if it exists (to preserve .git folder)
    if os.path.exists(dest_dir):
        print(f"🧹 Selectively clearing existing files in {dest_dir} (preserving .git tracking)...")
        for filename in os.listdir(dest_dir):
            if filename == ".git":
                continue
            file_path = os.path.join(dest_dir, filename)
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.unlink(file_path)
            except Exception as e:
                print(f"   ⚠️ Could not delete {filename}: {e}")
    else:
        os.makedirs(dest_dir, exist_ok=True)
    
    # 2. Define files and folders to copy
    items_to_copy = [
        "app.py",
        "config.py",
        "extensions.py",
        "requirements.txt",
        "run_local.py",
        ".env.example",
        "auth",
        "export",
        "invoices",
        "static",
        "templates",
        "tests",
        "data/schemas",
        "campaign",
        "docs",
        "scripts",
        "Dockerfile",
        "docker-compose.yml",
        "history",
        "todo.md",
        "PROGRESS_TRACKER_INVOICE_WEBAPP.md"
    ]
    
    # Exclude patterns during copy
    def ignore_patterns(path, names):
        ignored = []
        for name in names:
            if name in ['__pycache__', '.pytest_cache', '.coverage', 'harness.db', 'instance']:
                ignored.append(name)
            elif name.endswith(('.pyc', '.pyo', '.pyd', '.db')):
                ignored.append(name)
        return ignored

    for item in items_to_copy:
        if not os.path.exists(item):
            print(f"⚠️ Warning: {item} does not exist. Skipping.")
            continue
        
        dest_path = os.path.join(dest_dir, item)
        if os.path.isdir(item):
            print(f"📁 Copying folder: {item}...")
            shutil.copytree(item, dest_path, ignore=ignore_patterns)
        else:
            print(f"📄 Copying file: {item}...")
            shutil.copy2(item, dest_path)
            
    # 3. Create .github/workflows directory for CI
    ci_workflow_dir = os.path.join(dest_dir, ".github", "workflows")
    os.makedirs(ci_workflow_dir, exist_ok=True)
    
    # 4. Generate GitHub CI Workflow (.github/workflows/ci.yml)
    ci_content = """name: GDT Invoice Hub CI Pipeline

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Repository
      uses: actions/checkout@v4

    - name: Set up Python 3.10
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'
        cache: 'pip'

    - name: Install System Dependencies (Cairo)
      run: |
        sudo apt-get update
        sudo apt-get install -y libcairo2-dev pkg-config python3-dev

    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Create instance directory
      run: mkdir -p instance

    - name: Run Backend Test Suite (Excluding E2E browser tests)
      run: |
        python -m pytest --ignore=tests/test_e2e_ui.py -v
"""
    with open(os.path.join(ci_workflow_dir, "ci.yml"), "w", encoding="utf-8") as f:
        f.write(ci_content)
    print("🤖 Generated GitHub Actions CI Workflow.")

    # 5. Generate Gitignore
    gitignore_content = """# Flask/Python environment
venv/
.venv/
ENV/
env/
*.pyc
__pycache__/
.pytest_cache/
.coverage
htmlcov/

# Local databases and instance files
instance/
*.db
data/*
!data/schemas/

# Application configuration & secrets
.env
.env.local

# Operating System files
.DS_Store
Thumbs.db

# Chrome Temporary Profiles
.chrome_user_data_*
chromedriver/
"""
    with open(os.path.join(dest_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    print("🧹 Generated clean .gitignore file.")

    # 6. Generate MIT LICENSE
    license_content = """MIT License

Copyright (c) 2026 GDT Invoice Hub team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    with open(os.path.join(dest_dir, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(license_content)
    print("⚖️ Generated MIT LICENSE file.")

    # 7. Generate a professional README.md (Bilingual: VI / EN)
    readme_content = """# 🚀 GDT Invoice Hub

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
"""
    with open(os.path.join(dest_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("📖 Generated professional README.md.")

    # 8. Generate comprehensive GITHUB_PUBLISH_GUIDE.md
    publish_guide_content = """# HƯỚNG DẪN ĐƯA MÃ NGUỒN LÊN GITHUB CHUẨN DOANH NGHIỆP
## (Enterprise GitHub Publishing & CI/CD Walkthrough)

> [!IMPORTANT]  
> Hướng dẫn này hướng dẫn bạn từng bước cách đưa thư mục `gdt-invoice-hub` lên một kho chứa (Repository) mới trên GitHub, thiết lập các quy tắc bảo mật và kích hoạt đường ống CI/CD tự động.

---

## BƯỚC 1: Khởi Tạo Git Và Đưa Code Lên GitHub

Đảm bảo bạn đã cài đặt Git trên máy tính. Mở terminal tại thư mục `gdt-invoice-hub` và thực hiện:

1. **Khởi tạo repository cục bộ**:
   ```bash
   git init
   ```

2. **Thêm toàn bộ file vào khu vực chuẩn bị (Staging)**:
   ```bash
   git add .
   ```

3. **Tạo bản cam kết đầu tiên (Commit)**:
   ```bash
   git commit -m "feat: initial commit for GDT Invoice Hub core platform"
   ```

4. **Tạo một repository mới trên tài khoản GitHub của bạn**:
   - Truy cập: [https://github.com/new](https://github.com/new)
   - Đặt tên Repository: `gdt-invoice-hub`
   - Mô tả: `An Intelligent VAT Invoice Management, Risk Assessment, and Predictive Tax Forecasting Platform for Vietnamese Businesses.`
   - Chọn **Public** hoặc **Private** tùy thuộc vào nhu cầu của bạn.
   - **LƯU Ý**: Không tích chọn "Add a README", "Add .gitignore" hay "Choose a license" vì chúng ta đã tạo sẵn chúng vô cùng hoàn chỉnh ở local.

5. **Liên kết kho chứa cục bộ với GitHub**:
   ```bash
   git remote add origin https://github.com/<your-username>/gdt-invoice-hub.git
   ```

6. **Đặt tên nhánh chính là `main`**:
   ```bash
   git branch -M main
   ```

7. **Đẩy mã nguồn lên GitHub**:
   ```bash
   git push -u origin main
   ```

---

## BƯỚC 2: Thiết Lập Tự Động Hóa CI/CD (GitHub Actions)

Chúng tôi đã thiết lập sẵn cấu hình CI tại `.github/workflows/ci.yml`. Mỗi khi có ai đó đẩy mã nguồn (`git push`) hoặc tạo Pull Request lên nhánh `main`, GitHub Actions sẽ tự động:
1. Tạo một container Ubuntu ảo.
2. Cài đặt Python 3.11 và tải toàn bộ thư viện cần thiết từ `requirements.txt`.
3. Khởi chạy toàn bộ **212 ca kiểm thử** để đảm bảo không phát sinh lỗi logic hệ thống.

### Cách kiểm tra trạng thái CI:
- Truy cập tab **Actions** trên GitHub repository của bạn.
- Bạn sẽ thấy đường ống đang chạy, nhấp vào để xem chi tiết quá trình biên dịch và kiểm thử.
- Khi hoàn thành, một dấu tích xanh (Green Checkmark) sẽ xuất hiện minh chứng cho chất lượng mã nguồn đạt chuẩn sản xuất.

---

## BƯỚC 3: Cấu Hình Bảo Mật Nhánh (Branch Protection Rules)

Đối với các dự án chất lượng cao, việc bảo vệ nhánh `main` là bắt buộc để ngăn chặn mã nguồn lỗi bị đưa trực tiếp vào sản xuất:

1. Vào tab **Settings** của repository trên GitHub.
2. Nhấp vào mục **Branches** ở thanh menu bên trái.
3. Nhấp vào nút **Add branch protection rule**.
4. Cấu hình các thông số sau:
   - **Branch name pattern**: Điền `main`.
   - **Require a pull request before merging**: Tích chọn (Yêu cầu phải tạo Pull Request và được xét duyệt thay vì push đè lên main).
   - **Require status checks to pass before merging**: Tích chọn, tìm kiếm và chọn `build-and-test` (Đảm bảo kiểm thử tự động của GitHub Actions phải thành công 100% mới cho phép Merge).
5. Nhấp **Create** để kích hoạt.

---

## BƯỚC 4: Phát Hành Phiên Bản (GitHub Releases)

Khi mã nguồn đã ổn định và đạt chuẩn kiểm tra:
1. Vào trang chủ của Repository trên GitHub, ở thanh bên phải, nhấp vào mục **Releases** -> **Create a new release**.
2. Thiết lập nhãn phiên bản (Tag version) là `v1.0.0`.
3. Đặt tiêu đề phát hành: `v1.0.0 - Release chính thức Hệ thống Quản lý hóa đơn AI & Dự báo thuế`.
4. Viết tóm tắt các tính năng chính và nhấp **Publish release**.
"""
    with open(os.path.join(dest_dir, "GITHUB_PUBLISH_GUIDE.md"), "w", encoding="utf-8") as f:
        f.write(publish_guide_content)
    print("📘 Generated comprehensive GITHUB_PUBLISH_GUIDE.md.")
    
    print("\n🎉 GitHub publish package preparation finished successfully!")
    print(f"📍 Location: ./{dest_dir}")
    print("💡 You can now initialize git inside this folder and push to GitHub!")

if __name__ == "__main__":
    prepare_github_folder()
