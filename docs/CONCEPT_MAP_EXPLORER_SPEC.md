# Sơ đồ Khái niệm: Interactive Tax Compliance Concept Map Explorer

> **True Purpose:** Tôi cần mở bản đồ `Compliance Concept Map Explorer` để hiểu `cơ chế định tuyến và hiển thị tương tác các luật thuế v24-v70` trong bối cảnh `hệ thống GDT Invoice Hub`, nhằm `cải tiến trải nghiệm người dùng, giúp tra cứu và đối chiếu hóa đơn trực quan`.

---

## Focus Question
Làm thế nào để trực quan hóa toàn bộ mối quan hệ, ràng buộc và luồng dữ liệu của các luật tuân thủ thuế từ v24 đến v70 dưới dạng sơ đồ khái niệm (concept map) tương tác thời gian thực để hỗ trợ doanh nghiệp đối chiếu hóa đơn và kiểm toán nhanh?

---

## Trang 1: Định hướng (Orientation)
Hệ thống **Interactive Tax Compliance Concept Map Explorer** là một cải tiến UI/UX vượt trội cho GDT Invoice Hub. Thay vì bắt người dùng hoặc kiểm toán viên phải tìm kiếm thủ công qua hàng chục trang Compliance Hub riêng lẻ (từ v24 đến v70), trang bản đồ khái niệm này cung cấp một bản đồ mạng lưới (network graph) trực quan, cho phép người dùng click vào từng node (tương ứng với một phiên bản luật thuế/compliance hub), xem các mối liên kết, độ ưu tiên, trạng thái kích hoạt, và truy cập trực tiếp vào phân hệ đó.

---

## Trang 2: Mô hình Lõi (Core Model)
Mô hình lõi bao gồm các thành phần:
1. **Compliance Nodes**: Đại diện cho các luật thuế v24 - v70. Mỗi node có các thuộc tính:
   - Tên luật (e.g., EP Tax, CIT & TP, Special Consumption Tax).
   - Mức độ rủi ro (Low, Medium, High).
   - Trạng thái (Active, Pending, Deprecated).
2. **Reconciliation Links**: Các đường nối thể hiện quan hệ dữ liệu hoặc luồng nghiệp vụ giữa các luật thuế. Ví dụ: Luật hoàn thuế xuất khẩu v41 phụ thuộc vào dữ liệu VAT v47.
3. **Interactive Control Canvas**: Giao diện đồ họa SVG/D3/Cytoscape cho phép zoom, pan, tìm kiếm node, và highlight luồng rủi ro.

---

## Trang 3: Vòng đai Phạm vi (Scope Rings)

```
       +-----------------------------------------+
       | Frontier:                               |
       |  - AI tự phân tích và đề xuất liên kết  |
       |  - Dự báo rủi ro thuế bắc cầu          |
       +-----------------------------------------+
                    |
       +-----------------------------------------+
       | Adjacent:                               |
       |  - Liên kết trực tiếp tới các Hub       |
       |  - Chỉ số hiệu năng & thống kê nhanh    |
       +-----------------------------------------+
                    |
       +-----------------------------------------+
       | Core:                                   |
       |  - SVG Network Graph v24 - v70          |
       |  - Bộ lọc Trạng thái/Rủi ro/Loại thuế   |
       +-----------------------------------------+
```

- **Core (Giữ lại)**: SVG Network Graph biểu diễn các luật v24-v70, bộ lọc phân loại thuế, panel chi tiết khi click vào node.
- **Adjacent (Giữ lại)**: Liên kết trực tiếp chuyển trang, hiển thị số hóa đơn bị lỗi thuộc luật đó, tích hợp trạng thái thực tế từ DB.
- **Frontier (Cắt giảm giai đoạn 1)**: Đề xuất tự động bằng AI về các liên kết luật thuế mới dựa trên hóa đơn tải lên.
- **Out-of-scope (Không làm)**: Trực quan hóa chi tiết từng dòng code kiểm tra của luật thuế (chỉ trực quan hóa ở mức độ khái niệm và thống kê).

---

## Trang 4: Ngữ pháp Mối quan hệ (Relation Grammar)
Mối quan hệ giữa các phân hệ tuân thủ được phân loại như sau:

| Node A (Nguồn) | Loại Quan hệ | Node B (Đích) | Ý nghĩa nghiệp vụ |
|---|---|---|---|
| **v47 VAT Rate Hub** | `Prerequisite` | **v41 Export Refund** | Hoàn thuế xuất khẩu bắt buộc phải đối soát thuế suất VAT đầu vào trước. |
| **v53 EP Tax Hub** | `Subset` | **v61-v64 EP Details** | Các luật môi trường chi tiết (nước thải, khí thải, chất thải rắn) là phân hệ chuyên sâu của EP Tax. |
| **v45 CIT & TP Hub** | `Intersects` | **v49 CIT Law 67** | Luật giao dịch liên kết và quyết toán TNDN có vùng giao thoa về chi phí lãi vay được trừ. |

---

## Trang 5: Cơ chế & Vận hành (Mechanism & Dynamics)
1. **Dữ liệu Động (Dynamic Feed)**: Client tải trang -> Gửi request tới `/api/compliance/concept-map` -> Server truy vấn SQLite `harness.db` và lấy danh sách các hub đã đăng ký, trạng thái active, và số lỗi ghi nhận hiện tại.
2. **Vẽ Bản Đồ (SVG Rendering)**: Sử dụng HTML5 SVG và CSS animations để vẽ các node dưới dạng vòng tròn phát sáng (pulse) tùy theo mức độ rủi ro:
   - Đỏ rực: Rủi ro cao / Nhiều lỗi.
   - Vàng ấm: Rủi ro trung bình.
   - Xanh Wise: Hoàn toàn tuân thủ.
3. **Cơ chế Highlight**: Khi rê chuột (hover) vào một node, tất cả các node liên quan (adjacent nodes) và đường nối sẽ sáng lên, các node không liên quan sẽ mờ đi (fade out), tạo chiều sâu trải nghiệm thị giác.

---

## Trang 6: Ranh giới & Trường hợp Lỗi (Boundaries & Failure Cases)
- **Quá tải thông tin (Spaghetti Graph)**: Khi hiển thị tất cả 40+ luật thuế cùng lúc, biểu đồ có thể bị rối. 
  - *Giải pháp*: Cung cấp bộ lọc nhóm (Môi trường, Thu nhập, Giá trị gia tăng, Phí & Lệ phí) để người dùng có thể ẩn/hiện các nhóm node cụ thể.
- **Trạng thái không đồng bộ (Stale Cache)**: Trạng thái hóa đơn lỗi thay đổi nhưng biểu đồ chưa cập nhật.
  - *Giải pháp*: Sử dụng cơ chế Fetch API cập nhật bất đồng bộ mỗi khi người dùng thay đổi bộ lọc doanh nghiệp (MST).

---

## Trang 7: Lộ trình & Nghiệm thu (DoD)
- **Định nghĩa Hoàn thành (DoD)**:
  - [ ] Tạo route `/compliance-concept-map` trong `invoices/routes/core.py`.
  - [ ] Tạo giao diện `templates/compliance_concept_map.html` kế thừa `base.html` được thiết kế theo phong cách Wise Fintech/Premium Dark Mode.
  - [ ] Tích hợp thư viện đồ họa thuần SVG kết hợp CSS-in-JS linh hoạt, không phụ thuộc thư viện ngoài cồng kềnh để tối ưu tốc độ load.
  - [ ] Thêm liên kết truy cập bản đồ khái niệm vào menu chính của trang.
  - [ ] Viết unit/integration test xác thực route hoạt động và trả về HTTP 200.
  - [ ] Đăng ký Story trong Harness DB và chạy Unified Quality Gate để ký UAT report.
