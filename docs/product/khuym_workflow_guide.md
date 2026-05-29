# Hướng dẫn Vận hành Hệ thống Workflow Khuym (ag-kit)

Hệ thống **Khuym** là một bộ khung quy trình (workflow) phát triển phần mềm có độ tin cậy cao được đóng gói thành các skill của Codex/Claude. Quy trình này tập trung vào triết lý **"Kiểm chứng trước - Lập trình sau"**, giúp ngăn ngừa tối đa việc hiểu sai nghiệp vụ và hạn chế việc phải viết lại mã nguồn (rework) gây lãng phí tài nguyên.

---

## 1. Triết lý Vận hành: 6 Giai đoạn & 4 Cổng Phê duyệt (Gates)

Quy trình phát triển một tính năng hoặc giải quyết một vấn đề phức tạp qua Khuym trải qua 6 giai đoạn tuần tự và bắt buộc phải được phê duyệt bởi Con người (Human-in-the-loop) tại 4 thời điểm quan trọng:

```
[Yêu cầu] ➔ Exploring ➔ [GATE 1] ➔ Planning ➔ [GATE 2] ➔ Validating ➔ [GATE 3] ➔ Swarming/Executing ➔ Reviewing ➔ [GATE 4] ➔ Compounding
```

### 6 Giai đoạn Vận hành:
1. **`khuym:exploring` (Khảo sát)**: Agent thực hiện đối thoại Socratic ngắn để làm rõ yêu cầu mơ hồ, sau đó khóa các quyết định thiết kế vào tệp `history/<feature>/CONTEXT.md`.
2. **`khuym:planning` (Lập kế hoạch)**: Nghiên cứu cấu trúc code hiện có, đề xuất giải pháp kiến trúc và chia nhỏ công việc thành các Bead (nhiệm vụ độc lập).
3. **`khuym:validating` (Kiểm chứng)**: Chạy thử các đoạn mã thử nghiệm (spikes/probes) để chứng minh giải pháp kỹ thuật khả thi trước khi viết mã nguồn chính thức.
4. **`khuym:swarming` & `khuym:executing` (Triển khai)**: Điều phối các Agent thực hiện song song từng Bead, giữ các bản quyền file tránh xung đột thông qua tệp khóa `.khuym/reservations.json`.
5. **`khuym:reviewing` (Đánh giá)**: Chạy bộ kiểm thử tự động, đánh giá chất lượng mã nguồn, và phân cấp lỗi phát hiện (P1: Chặn merge, P2: Nghiêm trọng, P3: Khuyến nghị).
6. **`khuym:compounding` (Đúc kết)**: Tổng hợp các bài học kinh nghiệm thu được vào kho lưu trữ `history/learnings/` để các Agent tiếp theo kế thừa.

---

## 2. 4 Cổng Phê duyệt (Human Gates) - BẮT BUỘC

Khi chạy quy trình này, Agent **không bao giờ tự ý chuyển giai đoạn** nếu chưa được bạn phê duyệt rõ ràng:

* **GATE 1 (Sau Exploring)**: Bạn phê duyệt nội dung tệp `CONTEXT.md` (Đúng nghiệp vụ chưa?).
* **GATE 2 (Sau Planning)**: Bạn phê duyệt kiến trúc giải pháp và bảng phân rã Bead (Đúng thiết kế chưa?).
* **GATE 3 (Sau Validating)**: Bạn phê duyệt bằng chứng khả thi kỹ thuật (Code chạy thử thành công chưa?).
* **GATE 4 (Sau Reviewing)**: Các lỗi chặn P1 phải được sửa xong, bạn đồng ý tích hợp mã nguồn (Merge).

---

## 3. Các Lệnh Theo dõi & Giám sát Thời gian thực

Trong quá trình Agent làm việc, bạn có thể kiểm tra trạng thái sức khỏe của dự án và các phiên làm việc thông qua các lệnh Node.js đã được Onboard tự động vào Workspace:

### A. Kiểm tra nhanh trạng thái Onboarding & Giao lộ tiếp theo:
```bash
node .codex/khuym_status.mjs --json
```
* **Mục đích**: Xem dự án đã cài đặt thành công chưa, trạng thái của `state.json`, `HANDOFF.json` và đề xuất hành động tiếp theo.

### B. Kiểm tra danh sách file đang bị khóa bởi các Agent (File Leases/Reservations):
```bash
node .codex/khuym_reservations.mjs list --active-only --json
```
* **Mục đích**: Xem các file mã nguồn nào đang được khóa chỉnh sửa độc quyền bởi Agent nào để tránh xung đột mã nguồn.

### C. Quản lý công việc Bead (`br`):
* **Xem các nhiệm vụ đã sẵn sàng triển khai**: `br ready`
* **Xem chi tiết một Bead**: `br show <id>`
* **Cập nhật trạng thái Bead**: `br update <id> --status=in_progress`
* **Đồng bộ hóa dữ liệu Bead**: `br sync --flush-only`

---

## 4. Kịch bản Mẫu: Cách Hợp tác với Claude qua Khuym

Khi bạn muốn triển khai một tính năng mới (ví dụ: *"Thêm module phân tích hóa đơn rủi ro cao"*), hãy trò chuyện với Claude theo các bước sau:

### Bước 1: Yêu cầu Khảo sát (Exploring)
* **Bạn**: `Hãy bắt đầu khảo sát tính năng phân tích hóa đơn rủi ro cao bằng skill exploring.`
* **Claude**: Sẽ hỏi bạn một vài câu hỏi làm rõ nghiệp vụ, sau đó tạo file `history/risk_analysis/CONTEXT.md` ghi nhận các cam kết thiết kế. Claude sẽ yêu cầu bạn phê duyệt **GATE 1**.

### Bước 2: Lập kế hoạch (Planning)
* **Bạn**: `Tôi đồng ý với CONTEXT.md. Hãy lập kế hoạch chi tiết bằng planning.`
* **Claude**: Nghiên cứu cấu trúc code hiện tại, chia nhỏ các đầu việc thành các issue Bead (ví dụ: `br-150`, `br-151`), mô tả cách sửa code vào tệp thiết kế và yêu cầu phê duyệt **GATE 2**.

### Bước 3: Kiểm chứng kỹ thuật (Validating)
* **Bạn**: `Kế hoạch rất tốt. Hãy tiến hành kiểm chứng khả thi bằng validating.`
* **Claude**: Viết code giả lập (spike code) kiểm tra kết nối DB, API hoặc thư viện nghiệp vụ để đảm bảo không có rủi ro kỹ thuật ngầm. Báo cáo kết quả và yêu cầu phê duyệt **GATE 3**.

### Bước 4: Triển khai (Swarming & Executing)
* **Bạn**: `Bằng chứng rất thuyết phục. Tiến hành code đi!`
* **Claude**: Khóa các file cần sửa, triển khai code chính thức, chạy test tự động cục bộ, cập nhật trạng thái Bead sang `closed` và tự động đẩy mã nguồn lên Git.

### Bước 5: Đánh giá & Đúc kết (Reviewing & Compounding)
* **Claude**: Tiến hành review mã nguồn, phân tích rủi ro an ninh mạng và báo cáo chất lượng code. Sau khi bạn đồng ý merge (**GATE 4**), Claude sẽ chạy `compounding` để lưu các bài học rút ra vào `history/learnings/`.
