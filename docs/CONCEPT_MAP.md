# Bản đồ khái niệm: Hệ thống định tuyến Modular & Đối chiếu hóa đơn điện tử XML (Webapp XML)

> **Mode:** quality
> **Page count:** 7
> **True Purpose:** Tôi cần mở bản đồ hệ thống định tuyến modular và đối chiếu hóa đơn XML để hiểu rõ kiến trúc phân tách mã nguồn, cơ chế cô lập dữ liệu đa doanh nghiệp (multi-tenant), và luồng xử lý kiểm tra tuân thủ thuế tự động nhằm bảo trì và mở rộng hệ thống một cách an toàn, không gây lỗi hồi quy.
> **Focus Question:** Hệ thống định tuyến modular và cơ chế đối chiếu hóa đơn XML phối hợp với nhau như thế nào để đảm bảo dữ liệu hóa đơn từ Tổng cục Thuế (GDT) được cách ly an toàn theo từng taxpayer, kiểm tra tuân thủ tự động bằng bộ luật DSL, và xuất hồ sơ hoàn thuế VAT không lỗi?

---

## Trang 1 — Orientation: Vì sao mở bản đồ này?

Bản đồ khái niệm này cung cấp cái nhìn toàn cảnh về cách ứng dụng Webapp XML quản lý hàng triệu hóa đơn điện tử của các doanh nghiệp khác nhau dưới dạng XML, thực hiện kiểm tra tuân thủ phức tạp (từ các nghị định thuế của Việt Nam đến tiêu chuẩn kế toán quốc tế IFRS), đối chiếu với tờ khai hải quan và lập hồ sơ đề nghị hoàn thuế. 

Kiến trúc ban đầu của dự án tập trung toàn bộ các luồng xử lý HTTP vào một tệp duy nhất `invoices/routes.py` với quy mô hơn 13,000 dòng. Bản đồ này sẽ định hướng cho các kỹ sư phát triển cách hệ thống được phân rã thành các module chuyên biệt và cách các hạt giống nghiệp vụ liên kết chặt chẽ với nhau thông qua cơ chế phi tập trung.

| Thuộc tính | Nội dung chi tiết |
|---|---|
| **Hạt giống (Seed)** | Hệ thống định tuyến Modular & Đối chiếu hóa đơn điện tử XML (Webapp XML) |
| **Bối cảnh (Context)** | Framework Flask, SQLAlchemy (SQLite multi-tenant), các quy định pháp luật thuế Việt Nam (Nghị định 123, Thông tư 78, Luật 48, Luật 149), và nền tảng xử lý bất đồng bộ (Workers). |
| **Mục tiêu đầu ra** | Giúp nhà phát triển làm chủ mã nguồn sau phân rã, định vị nhanh chóng nơi cần sửa đổi khi luật thuế thay đổi, và thiết lập luồng tích hợp mới mà không tạo ra circular imports. |
| **Rủi ro lớn nhất** | Hiểu lầm về cơ chế chuyển đổi cơ sở dữ liệu tenant động (dynamic tenant switching) dẫn đến rò rỉ dữ liệu chéo giữa các doanh nghiệp hoặc lỗi ghi đè trạng thái. |

---

## Trang 2 — Core Model: Những node lõi

Hệ thống được vận hành dựa trên 6 khái niệm nền tảng. Dưới đây là lý do tại sao chúng quan trọng và những sai lầm có thể xảy ra nếu thiếu chúng.

| Khái niệm cốt lõi (Core Node) | Vai trò quan trọng trong hệ thống | Hậu quả nếu thiếu/hiểu sai khái niệm |
|---|---|---|
| **Modular Blueprints** | Phân rã định tuyến HTTP Flask thành các tệp độc lập (`core.py`, `reconciliation.py`, `ocr.py`, `compliance.py`, `mitigation.py`, `settings.py`) liên kết thông qua một blueprint chung duy nhất `invoices_blueprint`. | Gây ra lỗi import vòng (circular imports) khi khởi chạy Flask app, hoặc làm hỏng cơ chế phân giải URL (`url_for`) trong các template HTML. |
| **XML Parser Engine** | Đọc dữ liệu XML thô theo chuẩn hóa đơn GDT, kiểm tra tính toàn vẹn cấu trúc và giải nén dữ liệu dòng hàng (line items), thuế suất chi tiết. | Dữ liệu hóa đơn lưu vào DB sẽ bị sai lệch, thiếu thông tin chi tiết của từng dòng hàng, dẫn đến sai sót nghiêm trọng ở bước tính thuế suất. |
| **Multi-Tenant DB Layer** | Cơ chế cách ly dữ liệu động sử dụng một tệp SQLite riêng cho mỗi taxpayer dựa trên Mã số thuế (MST), chuyển đổi kết nối thông qua context local của SQLAlchemy. | Dữ liệu giữa các doanh nghiệp khác nhau sẽ bị trộn lẫn, vi phạm nghiêm trọng tính bảo mật thông tin tài chính doanh nghiệp. |
| **Compliance DSL Engine** | Ngôn ngữ đặc tả nghiệp vụ (Domain Specific Language) cho phép định nghĩa các quy tắc kiểm tra rủi ro thuế (ví dụ: hóa đơn đen, thanh toán tiền mặt vượt hạn mức). | Hệ thống trở nên cứng nhắc; mỗi khi luật thuế thay đổi, lập trình viên phải sửa đổi trực tiếp mã nguồn Python thay vì cập nhật rulebook. |
| **Background Workers** | Các tiến trình con chạy độc lập xử lý việc tải hóa đơn từ GDT, chạy phân tích OCR qua AI và đồng bộ dữ liệu nặng. | Luồng HTTP chính của Flask bị chặn (blocked), gây ra lỗi Timeout (HTTP 504) khi người dùng tải tệp lớn hoặc thực hiện đối chiếu hàng loạt. |
| **Cryptographic Ledger** | Sổ cái mật mã sử dụng Merkle Tree và bằng chứng không tiết lộ thông tin (ZKP) để ghi nhận dấu vết giao dịch hóa đơn và kiểm toán. | Hóa đơn có thể bị chỉnh sửa trái phép trong cơ sở dữ liệu mà không bị phát hiện, làm mất đi tính minh chứng pháp lý khi cơ quan thuế thanh tra. |

---

## Trang 3 — Scope Rings: Phân vùng phạm vi hệ thống

Để tránh việc phình to phạm vi thiết kế (scope creep), hệ thống được chia rõ ràng thành 4 vòng phạm vi từ lõi ra đến ngoài biên.

```
       [ Vòng 4: Nằm Ngoài Phạm Vi (Kế toán nội bộ, Cổng thanh toán) ]
     [ Vòng 3: Ranh Giới (ZKP, Merkle Ledger, AI Data Repair) ]
   [ Vòng 2: Lân Cận (OCR số hóa, Xuất PDF/Excel, GDT API Integration) ]
 [ Vòng 1: Cốt Lõi (Modular Blueprints, XML Parser, Multi-Tenant DB, DSL) ]
```

| Vòng phạm vi (Ring) | Các thành phần bao gồm | Lý do phân loại |
|---|---|---|
| **Vòng 1: Cốt lõi (Core)** | - Định tuyến Modular (`invoices/routes/`) <br>- Bộ parse XML hóa đơn <br>- Cô lập cơ sở dữ liệu taxpayer <br>- Bộ chấm điểm rủi ro thuế (T-Score) | Đây là các thành phần bắt buộc phải hoạt động để hệ thống có thể thực hiện chức năng cơ bản nhất là lưu trữ và hiển thị hóa đơn an toàn. |
| **Vòng 2: Lân cận (Adjacent)** | - Dịch vụ số hóa OCR hóa đơn giấy <br>- Bộ tạo file PDF & xuất Excel <br>- API giả lập GDT Sandbox | Các thành phần hỗ trợ người dùng chuyển đổi dữ liệu vật lý sang số hóa và báo cáo kết quả, nhưng không thay đổi cấu trúc dữ liệu nền tảng. |
| **Vòng 3: Ranh giới (Frontier)** | - Chứng minh ZKP tuân thủ thuế <br>- Sổ cái bảo vệ Merkle Tree <br>- Sửa lỗi dữ liệu bằng AI (Ollama) | Các tính năng nâng cao nhằm tăng cường bảo mật và tự động hóa sửa lỗi dữ liệu. Có thể tạm thời vô hiệu hóa mà không làm hỏng luồng nghiệp vụ chính. |
| **Vòng 4: Ngoài biên (Out-of-scope)** | - Hệ thống kế toán kép (Double-entry) <br>- Cổng thanh toán hóa đơn trực tuyến <br>- Giao diện quản trị hosting hạ tầng | Các chức năng này thuộc về phần mềm kế toán hoặc quản lý hạ tầng chuyên dụng, không nằm trong mục tiêu của Webapp đối chiếu hóa đơn XML. |

---

## Trang 4 — Relation Grammar: Ngữ pháp mối quan hệ

Mối quan hệ giữa các thành phần không phải là các liên kết tĩnh mà là các luồng tương tác có điều kiện và ràng buộc chặt chẽ.

```
[Modular Blueprints] --(Đăng ký định tuyến thông qua)--> [Shared Blueprint State]
[XML Parser Engine]  --(Tạo đối tượng hóa đơn lưu vào)--> [Multi-Tenant DB Layer]
[Multi-Tenant DB]    --(Cung cấp dữ liệu đầu vào cho)--> [Compliance DSL Engine]
[Compliance DSL]     --(Sinh điểm số rủi ro thuế)------> [T-Score Scoreboard]
[Background Workers] --(Chạy không đồng bộ, ghi vào)---> [Cryptographic Ledger]
```

* **Quy tắc Định tuyến**: *Modular Blueprints* (`core.py`, `compliance.py`,...) không tự định nghĩa Blueprint riêng lẻ mà cùng import và đăng ký handler lên đối tượng chung `invoices_blueprint` nằm tại `shared.py`. Điều này giải quyết triệt để lỗi import vòng khi ứng dụng Flask khởi tạo.
* **Quy tắc Lưu trữ & Đối chiếu**: Sau khi *XML Parser Engine* xử lý tệp XML tải từ GDT, nó phải kiểm tra mã số thuế của người mua/bán để gọi *Tenant Switcher*, gắn kết nối SQLAlchemy vào đúng cơ sở dữ liệu SQLite của taxpayer đó, sau đó mới thực hiện lưu trữ thông tin.
* **Quy tắc Đánh giá Tuân thủ**: Dữ liệu hóa đơn sau khi được lưu vào cơ sở dữ liệu tenant sẽ tự động kích hoạt *Compliance DSL Engine* để quét qua các quy tắc hoạt động. Kết quả quét sẽ sinh ra điểm số rủi ro thuế (*T-Score*) và nếu điểm rủi ro vượt ngưỡng, hệ thống sẽ đề xuất tạo thư giải trình tại *Mitigation Module*.
* **Quy tắc Bảo mật**: Các tác vụ xử lý lô lớn do *Background Workers* thực hiện phải liên tục cập nhật mã băm trạng thái (hash state) của cơ sở dữ liệu vào *Cryptographic Ledger* để đảm bảo dữ liệu không bị can thiệp vật lý trong quá trình xử lý ngầm.

---

## Trang 5 — Mechanism & Dynamics: Cơ chế vận hành luồng dữ liệu

Biểu đồ dưới đây mô tả chi tiết cách một tệp hóa đơn XML đi từ khi tải lên đến khi được phân tích tuân thủ và xuất hồ sơ hoàn thuế.

```text
[Tệp XML hóa đơn] 
       │
       ▼
┌────────────────────────┐
│  Request Interceptor   │ ──(Lấy thông tin MST của Taxpayer đang log-in)
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│     Tenant Switcher    │ ──(Kết nối tới file DB SQLite: tenant_<MST>.db)
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│   XML Parser Engine    │ ──(Giải mã hóa đơn, ký số HSM, kiểm tra thẻ XML)
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│     Database Save      │ ──(Lưu Invoice, InvoiceItems, Supplier thông tin)
└────────────────────────┘
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
┌────────────────────────┐             ┌────────────────────────┐
│ Compliance DSL Engine  │             │   Merkle Tree Ledger   │
└────────────────────────┘             └────────────────────────┘
       │ (Quét các rule)                         │ (Ghi mã băm hóa đơn)
       ▼                                         ▼
┌────────────────────────┐             ┌────────────────────────┐
│   T-Score Generator    │             │   Cryptographic Proof  │
└────────────────────────┘             └────────────────────────┘
       │
       ▼
┌────────────────────────┐
│  VAT Refund Optimizer  │ ──(Đối chiếu tờ khai hải quan -> Xuất hồ sơ PDF)
└────────────────────────┘
```

### Chi tiết hoạt động và rủi ro ở từng giai đoạn:

1. **Nhận dạng và Định tuyến Tenant**:
   * *Cơ chế*: Khi người dùng gửi request (tải lên XML hoặc yêu cầu đồng bộ từ GDT), Flask middleware sẽ trích xuất MST của doanh nghiệp hiện tại và chuyển cấu hình kết nối DB sang tệp SQLite tương ứng.
   * *Rủi ro lỗi*: Nếu cơ chế luân chuyển tenant thất bại hoặc không giải phóng kết nối cũ (connection pooling leak), dữ liệu của taxpayer A có thể bị ghi nhầm vào DB của taxpayer B.

2. **Phân tích cú pháp & Chuẩn hóa dữ liệu (Parsing)**:
   * *Cơ chế*: XML Parser bóc tách các trường thông tin chính: Ký hiệu hóa đơn, số hóa đơn, ngày lập, thông tin người bán, danh mục hàng hóa, thuế suất VAT (0%, 5%, 8%, 10%), tổng tiền trước và sau thuế.
   * *Rủi ro lỗi*: Các tệp XML từ GDT đôi khi chứa ký tự lạ hoặc định dạng ngày tháng không chuẩn, có thể làm sập parser nếu không có các khối `try-except` bọc ngoài và hệ thống sửa lỗi tự động.

3. **Chấm điểm tuân thủ & Phát hiện rủi ro (Compliance & Scoring)**:
   * *Cơ chế*: Dựa trên các quy tắc DSL được thiết lập (ví dụ: "Nhà cung cấp nằm trong danh sách đen cảnh báo thuế", "Hóa đơn mua vào trên 20 triệu thanh toán bằng tiền mặt"), hệ thống sẽ trừ điểm T-Score từ mốc 100 điểm chuẩn.
   * *Rủi ro lỗi*: Quy tắc DSL viết sai logic toán tử có thể dẫn đến việc báo cáo sai lệch rủi ro (False Positive), khóa nhầm các hóa đơn hợp lệ của doanh nghiệp.

4. **Đồng bộ và Bảo vệ toàn vẹn (Sổ cái mật mã)**:
   * *Cơ chế*: Mỗi hóa đơn mới lưu trữ sẽ được băm (hash) cùng với mã băm của hóa đơn trước đó để tạo thành Merkle Tree. Mã băm gốc (Root Hash) được lưu trữ tại cấu trúc sổ cái bất biến.
   * *Rủi ro lỗi*: Việc tính toán hash liên tục trên luồng HTTP có thể làm giảm hiệu năng hệ thống, cần được tối ưu hoặc tính toán song song.

---

## Trang 6 — Boundaries & Failure Cases: Ranh giới sử dụng & Kịch bản lỗi

Hệ thống được thiết kế để vận hành tối ưu trong phạm vi định trước. Dưới đây là các ranh giới công nghệ và kịch bản lỗi thường gặp cùng cách xử lý.

| Kịch bản thực tế | Cách ứng phó đúng đắn | Lý do kỹ thuật & Nguyên tắc thiết kế |
|---|---|---|
| **Người dùng yêu cầu tải lên tệp XML dung lượng cực lớn (lô hàng nghìn hóa đơn)** | Tránh xử lý đồng bộ trực tiếp trong view function của Flask. Đẩy tệp vào hàng đợi và kích hoạt **Background Worker** xử lý bất đồng bộ, trả về task ID cho client để theo dõi tiến độ qua AJAX/SSE. | Luồng xử lý HTTP của Flask có thời hạn timeout ngắn (thường là 30s-60s). Nếu xử lý tệp lớn đồng bộ, trình duyệt sẽ báo lỗi Gateway Timeout (HTTP 504) mặc dù hệ thống vẫn đang chạy ngầm. |
| **Một quy tắc thuế mới (ví dụ: Giảm thuế VAT xuống 8% theo Nghị quyết mới) được ban hành** | Cập nhật cấu hình rulebook thông qua **Compliance DSL Interface** hoặc cập nhật cấu trúc ánh xạ trong `invoices/routes/compliance.py` thay vì can thiệp vào bộ lõi xử lý dữ liệu. | Việc cô lập logic quy định thuế vào module `compliance` giúp bảo vệ bộ parser XML và cấu trúc dữ liệu lưu trữ không bị ảnh hưởng khi chính sách thuế thay đổi liên tục. |
| **Cơ sở dữ liệu của một Tenant bị hỏng cấu trúc (Corrupted SQLite file)** | Hệ thống tự động phát hiện lỗi kiểm tra mã băm Merkle Tree, cách ly file DB bị hỏng, thông báo cho quản trị viên và chuyển sang chế độ đọc ghi giới hạn, sử dụng tệp sao lưu gần nhất. | Tính năng Multi-tenant độc lập cho phép cô lập hoàn toàn sự cố lỗi tệp tin. Database của một doanh nghiệp bị lỗi sẽ không làm ảnh hưởng đến hoạt động của các doanh nghiệp khác. |
| **API kết nối trực tiếp đến hệ thống hóa đơn điện tử GDT bị nghẽn mạng** | Chuyển sang cơ chế xếp hàng đợi tác vụ tải (retry queue) với thuật toán Exponential Backoff và kích hoạt giả lập Sandbox nếu đang ở môi trường kiểm thử. | Ngăn chặn việc hệ thống bị treo khi gọi các dịch vụ bên thứ ba chậm phản hồi, đảm bảo trải nghiệm người dùng luôn mượt mà. |

---

## Trang 7 — Application, Learning Path & DoD

### Lộ trình học tập & Phát triển tính năng (Learning Path)

Để làm chủ và phát triển hệ thống này, các kỹ sư nên tuân theo lộ trình 3 bước sau:

* **Mức độ 1: Nhập môn (Beginner)**:
  * *Mục tiêu*: Hiểu cấu trúc thư mục định tuyến modular mới và cách đăng ký route thông qua `invoices_blueprint`.
  * *Bài tập thực hành*: Thêm một endpoint kiểm tra trạng thái đơn giản trong `invoices/routes/settings.py` và sử dụng `url_for('invoices.your_endpoint')` để hiển thị trên giao diện.
* **Mức độ 2: Trung cấp (Intermediate)**:
  * *Mục tiêu*: Nắm vững luồng hoạt động của XML Parser và Tenant Switcher.
  * *Bài tập thực hành*: Viết một bộ test case giả lập tải lên một file XML bị lỗi thẻ để kiểm tra cơ chế tự động sửa lỗi và ghi nhật ký cảnh báo an toàn.
* **Mức độ 3: Nâng cao (Advanced)**:
  * *Mục tiêu*: Tối ưu hóa hiệu năng đối chiếu dữ liệu hóa đơn số lượng lớn và tùy biến luật đánh giá thuế DSL nâng cao.
  * *Bài tập thực hành*: Thiết lập quy tắc kiểm tra rủi ro liên kết giữa hai hóa đơn mua vào - bán ra của cùng một nhà cung cấp và đo lường thời gian xử lý khi chạy song song qua Background Workers.

### Nén thông tin theo nguyên lý 80/20 (80/20 Compression)

* **Bắt buộc phải biết (Must-know)**:
  * Cơ chế đăng ký route phi tập trung trong `invoices/routes/` để tránh lỗi import vòng.
  * Cách trích xuất MST từ session người dùng để định tuyến kết nối SQLite động.
* **Nên biết (Should-know)**:
  * Cách thức hoạt động của bộ đánh giá rủi ro tuân thủ thuế T-Score và các lỗi VAT thường gặp.
  * Cách sử dụng Background Workers để đẩy các tác vụ nặng ra khỏi luồng HTTP chính.
* **Học sau (Later)**:
  * Cơ chế tạo bằng chứng ZKP và bảo mật sổ cái mật mã Merkle Tree.
* **Loại bỏ (Cut)**:
  * Các tính năng phân tích tài chính sâu ngoài phạm vi kiểm tra tuân thủ thuế và lập hồ sơ hoàn thuế VAT.

### Tiêu chuẩn hoàn thành kiểm tra chất lượng (Quality Check)

- [ ] Bản đồ khái niệm đã bao quát đầy đủ 7 trang cấu trúc chuẩn.
- [ ] Định rõ Focus Question và True Purpose liên quan trực tiếp đến dự án Webapp XML.
- [ ] Đã phân tách ranh giới rõ ràng giữa các thành phần cốt lõi và các tính năng nâng cao.
- [ ] Các mối quan hệ kỹ thuật được chuyển hóa thành các mệnh đề logic hoạt động chi tiết.
- [ ] Bản đồ cung cấp đầy đủ thông tin về luồng xử lý dữ liệu, ranh giới lỗi và lộ trình phát triển.
- [ ] Người đọc có thể giải thích được cách thức hoạt động của hệ thống multi-tenant và module định tuyến mới sau khi nghiên cứu bản đồ này.
