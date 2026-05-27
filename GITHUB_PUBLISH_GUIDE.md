# HƯỚNG DẪN ĐƯA MÃ NGUỒN LÊN GITHUB CHUẨN DOANH NGHIỆP
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
