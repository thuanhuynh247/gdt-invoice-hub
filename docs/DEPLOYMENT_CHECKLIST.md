# ✅ CHECKLIST TRIỂN KHAI SẢN XUẤT (Production Deployment Checklist)
# GDT Invoice Hub v17.0.0

---

## 📋 Giai đoạn 1: Trước UAT (Pre-UAT)

- [x] Toàn bộ 205 User Stories đã triển khai
- [x] 448/449 automated tests PASSED (1 skipped E2E)
- [x] 19/19 UAT smoke tests PASSED
- [x] Harness.db đồng bộ trạng thái `implemented`
- [x] Tài liệu UAT Plan tạo xong (`docs/UAT_PLAN.md`)
- [x] Hướng dẫn sử dụng tạo xong (`docs/USER_MANUAL.md`)
- [x] Script khởi chạy UAT tạo xong (`UAT_LAUNCH.bat`)
- [x] Script smoke test tạo xong (`scripts/uat_smoke_test.py`)

---

## 📋 Giai đoạn 2: Trong UAT

- [ ] Chạy 12 kịch bản kiểm thử (TC-001 đến TC-012)
- [ ] Ghi nhận bug theo mẫu (nếu có)
- [ ] Sửa bug và chạy kiểm thử hồi quy
- [ ] Xác nhận hiệu năng API ≤ 3s
- [ ] Kiểm tra bảo mật phân quyền RBAC
- [ ] Kiểm tra cách ly dữ liệu đa MST
- [ ] Ký biên bản nghiệm thu UAT

---

## 📋 Giai đoạn 3: Chuẩn bị Production

- [ ] Cập nhật `.env` với thông tin thực:
  - [ ] `GDT_USERNAME` = MST thực
  - [ ] `GDT_PASSWORD` = Mật khẩu thực
  - [ ] `FLASK_SECRET_KEY` = Khóa bảo mật mạnh (32+ ký tự)
  - [ ] `GDT_USE_MOCK` = `false`
  - [ ] `FLASK_DEBUG` = `false`
- [ ] Thiết lập Telegram Bot Token (nếu dùng cảnh báo)
- [ ] Thiết lập SMTP Email (nếu dùng email cảnh báo)
- [ ] Xóa dữ liệu mock trong `data/invoices.db` (backup trước)
- [ ] Kiểm tra dung lượng ổ đĩa ≥ 1GB trống

---

## 📋 Giai đoạn 4: Go-Live

- [ ] Chạy `python run_local.py` trên máy sản xuất
  - HOẶC: `docker-compose up -d` (nếu dùng Docker)
- [ ] Đăng nhập bằng tài khoản GDT thật
- [ ] Tra cứu hóa đơn tháng hiện tại → Xác nhận dữ liệu chính xác
- [ ] Chạy kiểm toán AI trên 5 hóa đơn mẫu
- [ ] Xuất Excel → Đối chiếu với dữ liệu trên cổng GDT
- [ ] Thiết lập lịch sao lưu hàng ngày (`data/` → USB hoặc Cloud)

---

## 📋 Giai đoạn 5: Bảo trì (Ongoing)

- [ ] Theo dõi thay đổi API của `gdt.gov.vn` (hàng tháng)
- [ ] Cập nhật Danh sách đen MST (hàng quý)
- [ ] Sao lưu `data/invoices.db` hàng ngày
- [ ] Cập nhật luật thuế mới vào RAG engine (khi có thông tư mới)
- [ ] Kiểm tra dung lượng ổ đĩa hàng tháng
- [ ] Cập nhật `requirements.txt` khi có bản vá bảo mật
