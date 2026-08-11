---
name: webapp-improvement-loop
description: |
  Tự động thực hiện vòng lặp phân tích, sửa đổi mã nguồn, chạy kiểm thử và 
  tối ưu hóa UI/UX cho ứng dụng web theo tiêu chuẩn Wise Fintech. Kích hoạt khi 
  người dùng yêu cầu "cải tiến webapp", "chạy vòng lặp tối ưu", "run improvement loop", 
  "tối ưu UI & test", hoặc các yêu cầu tương tự liên quan đến nâng cấp giao diện và chất lượng code.
---

# Goal
Tự động phát hiện lỗi, nâng cấp giao diện chuẩn Wise Fintech, sửa code, đảm bảo 100% test suite vượt qua thành công và đồng bộ telemetry đầy đủ vào Harness.

# Instructions
1. **Khảo sát Tài nguyên & Bề mặt (Pre-check & Scout)**:
   - **Kiểm tra Đĩa Trống:** Thực hiện kiểm tra dung lượng ổ đĩa khả dụng. Nếu ổ đĩa hệ thống (`C:`) có dung lượng trống thấp (< 500MB), cấu hình biến môi trường trỏ cache sang ổ lớn hơn (`D:`).
   - **Quét UI/UX:** Quét các tệp HTML, JS, CSS đang mở hoặc các thay đổi gần đây để đối chiếu với các nguyên tắc thiết kế của Wise Fintech.
   - **Kiểm tra WAL & DB Lock:** Đảm bảo SQLite WAL Mode được kích hoạt để tránh khóa ghi tệp cơ sở dữ liệu khi chạy test.

2. **Lên Kế hoạch Cải tiến (Plan)**:
   - Viết các đề xuất cải tiến cấu trúc, màu sắc hoặc logic cụ thể vào `implementation_plan.md`.

3. **Thực thi Thay đổi (Execute)**:
   - Sử dụng các công cụ chỉnh sửa tệp chuyên biệt (`replace_file_content` hoặc `multi_replace_file_content`) để thực hiện các thay đổi mã nguồn.
   - Giữ nguyên toàn bộ các chú thích và docstring không liên quan trực tiếp đến sửa đổi.

4. **Kiểm thử Phân cấp & Sửa lỗi (Cascading Verification Loop)**:
   - **Cấp độ 1 (Targeted):** Ưu tiên chạy các tệp kiểm thử (`pytest`) liên quan trực tiếp đến module hoặc luồng tính toán vừa thay đổi.
   - **Cấp độ 2 (Global Validation):** Chạy `pytest` toàn bộ hoặc `python -m pytest tests/`.
   - **Cơ chế Fallback khi Crash:** Nếu quá trình kiểm thử toàn bộ bị crash, lập tức chuyển sang chạy cô lập các tệp test riêng lẻ.
   - **Vòng lặp khắc phục:** Nếu test thất bại, phân tích traceback lỗi, cập nhật mã nguồn và chạy lại test (tối đa 3 vòng lặp).

5. **Đồng bộ Harness & Nghiệm thu (Compounding)**:
   - Ghi nhận đầy đủ các thay đổi và kết quả kiểm thử vào tệp `walkthrough.md`.
   - Cập nhật tiến độ hoàn thành trong tệp `task.md`.
   - Thực hiện lệnh `python scripts/harness_win.py unified-gate` và `trace` nếu cần ghi nhận telemetry vào `harness.db`.

# Constraints
- 🚫 **Tuyệt đối không xóa file gốc vĩnh viễn**: Nếu cần loại bỏ tệp tin, di chuyển chúng vào thư mục `_Delete/` ở thư mục gốc.
- 🎨 **Bảng mã màu & Typography:** Tuân thủ tuyệt đối các chuẩn thiết kế Wise Fintech (Mã màu HSL, Font Outfit & Inter, Bento Grid, Glassmorphism).
- ⚙️ **Bắt buộc chạy test:** Mọi thay đổi logic đều phải vượt qua kiểm thử trước khi bàn giao.
