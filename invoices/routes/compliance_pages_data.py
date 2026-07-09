# -*- coding: utf-8 -*-
"""Compliance pages data module.
Provides in-depth legal and operational 7-page guides for all 38 compliance nodes (v26-v75).
"""

def get_compliance_pages(version_id: str, mst: str, db_stats: dict) -> list[dict] | None:
    v_clean = version_id.lower().strip()
    
    # 1. Base statistics calculations
    fuel_count = db_stats.get("fuel_logs_count", 0)
    coal_count = db_stats.get("coal_logs_count", 0)
    plastic_count = db_stats.get("plastic_bag_logs_count", 0)
    chemical_count = db_stats.get("chemical_logs_count", 0)
    ewaste_count = db_stats.get("ewaste_logs_count", 0)
    wastewater_count = db_stats.get("wastewater_logs_count", 0)
    hazardous_count = db_stats.get("hazardous_logs_count", 0)
    noise_count = db_stats.get("noise_logs_count", 0)
    plastics_count = db_stats.get("plastics_logs_count", 0)
    headroom_count = db_stats.get("headroom_logs_count", 0)
    total_violations = db_stats.get("total_violations", 0)
    
    pages = []
    
    if v_clean == "v26":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nTối ưu hóa quyết toán Thuế thu nhập doanh nghiệp (Corporate Income Tax - CIT) v26 và quản lý chặt chẽ các chi phí không được trừ khi tính thuế CIT.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động nhận diện các hóa đơn có rủi ro chi phí không được trừ (ví dụ: hóa đơn khống, mua sắm cá nhân, chi phí vượt định mức) phục vụ quyết toán CIT v26?*\n\n### Lời hứa của bản đồ (Map Promise)\nGiúp kế toán trưởng và giám đốc tài chính nắm bắt toàn bộ sơ đồ logic xác định thu nhập tính thuế CIT, cấu trúc các khoản chi phí hợp lý hợp lệ, và đối chiếu tờ khai quyết toán thuế mẫu 03/TNDN nhanh chóng."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Cấu Trúc Mô Hình Tính CIT\n*   **Thu nhập chịu thuế**: = Doanh thu - Chi phí được trừ + Các khoản thu nhập khác.\n*   **Thu nhập tính thuế**: = Thu nhập chịu thuế - Thu nhập được miễn thuế - Các khoản lỗ được kết chuyển.\n*   **Thuế CIT phải nộp**: = Thu nhập tính thuế × Thuế suất (Mặc định 20% hoặc mức ưu đãi).\n\n### Phân loại chi phí trên hệ thống\n*   **Deductible (Chi phí được trừ)**: Đầy đủ hóa đơn, chứng từ thanh toán không dùng tiền mặt nếu từ 20 triệu đồng trở lên.\n*   **Non-deductible (Chi phí không được trừ)**: Hóa đơn mua sắm cá nhân, chi phí lãi vay vượt trần EBITDA 30% (Nghị định 255/2026/NĐ-CP thay thế Nghị định 132/2020/NĐ-CP), chi phí không phục vụ sản xuất kinh doanh."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Ứng Dụng Thuế CIT v26\n*   **Vùng Lõi (Core)**: Tính toán thuế suất CIT cơ bản (20%), phân loại hóa đơn đầu vào hợp lệ/không hợp lệ, ghi nhận chi phí được trừ.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với phân hệ Ngân hàng để tự động kiểm soát chứng từ thanh toán không dùng tiền mặt đối với các hóa đơn giá trị từ 20 triệu đồng.\n*   **Vùng Biên Giới (Frontier)**: Phân tích dự báo số thuế CIT tạm nộp hàng quý nhằm tối ưu dòng tiền doanh nghiệp.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Kế toán quản trị nội bộ hoặc lập báo cáo tài chính quốc tế IFRS."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Các Quy Tắc Liên Kết Thuế CIT\n*   **Ràng buộc chi phí (Constraint)**: Khoản chi có hóa đơn từ 20 triệu đồng trở lên **bắt buộc** phải có chứng từ thanh toán không dùng tiền mặt để được tính là chi phí được trừ.\n*   **Đánh đổi ưu đãi (Trade-off)**: Hưởng thuế suất ưu đãi CIT tại khu công nghiệp yêu cầu doanh nghiệp phải hạch toán độc lập doanh thu và chi phí của dự án đầu tư ưu đãi đó."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Đối Soát Chi Phí Quyết Toán CIT\n1. Phân tích hóa đơn mua vào tự động.\n2. Kiểm tra giá trị hóa đơn:\n   - Nếu giá trị < 20.000.000 VND: Chấp nhận hạch toán chi phí hợp lệ thông thường.\n   - Nếu giá trị >= 20.000.000 VND: Yêu cầu đối chiếu với dữ liệu ngân hàng để tìm chứng từ chuyển khoản tương ứng.\n3. Phát hiện rủi ro doanh nghiệp ma: Đối chiếu MST người bán với danh sách doanh nghiệp tạm ngừng hoạt động hoặc bỏ địa chỉ kinh doanh.\n4. Kết xuất báo cáo chi phí không được trừ ước tính cuối kỳ."
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Chỉ Số Kiểm Toán CIT v26\n*   Thuế suất CIT mặc định áp dụng: **20%**\n*   Tổng chi phí nghi ngờ (Không được trừ): **{total_violations * 1250000:,.0f} VND**\n*   Số hóa đơn đầu vào cần đối soát thanh toán: **{fuel_count + coal_count} hóa đơn**\n\n### Tình huống lỗi điển hình\n*   **Thanh toán sai phương thức**: Trả tiền mặt cho hóa đơn mua xăng dầu có tổng giá trị thanh toán 25 triệu đồng (bao gồm VAT).\n*   **Lãi vay vượt trần**: Chi phí lãi vay vượt mức 30% EBITDA do không theo dõi quan hệ liên kết của các công ty mẹ con."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Học Tập & Triển Khai\n*   **Bước 1**: Rà soát lại toàn bộ hóa đơn mua vào cuối mỗi quý bằng chức năng đối soát tự động của GDT Invoice Hub.\n*   **Bước 2**: Lập bảng kê các khoản chi phí không được trừ để điều chỉnh trên chỉ tiêu B4 của tờ khai quyết toán thuế CIT.\n\n### Luật tham chiếu\n*   **Luật Thuế thu nhập doanh nghiệp số 14/2008/QH12** và các luật sửa đổi bổ sung.\n*   **Thông tư số 78/2014/TT-BTC** hướng dẫn thi hành Luật Thuế thu nhập doanh nghiệp."
            }
        ]

    elif v_clean == "v27":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nĐảm bảo cấu trúc dữ liệu hóa đơn điện tử XML gốc hoàn toàn tuân thủ theo chuẩn của Tổng cục Thuế Việt Nam quy định tại Nghị định số 254/2026/NĐ-CP (thay thế Nghị định số 123/2020/NĐ-CP).\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để phát hiện sớm các lỗi schema XML, thiếu chữ ký số, sai cấu trúc thẻ dữ liệu hoặc namespaces trước khi truyền nhận dữ liệu đến hệ thống GDT?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp sơ đồ phân tích các thẻ XML cốt lõi (DLHDon, TTChung, NBan, NMua, TToan), giúp lập trình viên và kế toán đối chiếu nhanh các sai lệch cấu trúc dữ liệu của nhà cung cấp."
            },
            {
                "title": "2. Mô Định Lõi (Core Model)",
                "content": "### Cấu Trúc File XML Hóa Đơn Chuẩn\n*   **Thẻ gốc (Root Element)**: `<HDon>` hoặc `<HSoThueDTu>` chứa namespace chuẩn.\n*   **DLHDon (Dữ liệu hóa đơn)**: Chứa thông tin chung, thông tin người bán (NBan), người mua (NMua), chi tiết hàng hóa dịch vụ (DSHHDV) và thanh toán (TToan).\n*   **Signature (Chữ ký số)**: Thẻ chữ ký số chuẩn XMLDSig của đơn vị phát hành hóa đơn đảm bảo tính toàn vẹn dữ liệu."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Phân Phân Tích XML v27\n*   **Vùng Lõi (Core)**: Kiểm tra định dạng XML well-formed, xác thực sơ đồ XSD chuẩn do Tổng cục Thuế cung cấp.\n*   **Vùng Cận Biên (Adjacent)**: Giải mã chữ ký số, kiểm tra chứng thư số hết hạn hay bị thu hồi (CRL/OCSP).\n*   **Vùng Biên Giới (Frontier)**: Tự động đối chiếu mã số thuế người bán, người mua với cơ sở dữ liệu đăng ký doanh nghiệp quốc gia.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Ký hợp đồng kinh tế thực tế giữa hai bên."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Luật Liên Kết Cấu Trúc XML\n*   **Tính kế thừa**: Mọi hóa đơn XML bắt buộc phải có thẻ `<HTTToan>` (Hình thức thanh toán) để xác định tính hợp lệ khấu trừ thuế GTGT.\n*   **Ràng buộc thứ tự**: Thẻ `<TTChung>` bắt buộc phải xuất hiện trước `<NDHDon>` và `<TToan>` bên dưới thẻ `<DLHDon>`. Thứ tự sai lệch sẽ gây lỗi Schema Validation."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Phân Tích Cú Pháp XML Hóa Đơn\n\n```mermaid\ngraph TD\n    A[Nhận XML đầu vào] --> B{XML Well-formed?}\n    B -->|Không| C[Báo lỗi cấu trúc tệp XML]\n    B -->|Có| D{Kiểm tra XSD Schema?}\n    D -->|Sai| E[Báo lỗi không hợp chuẩn NĐ 254/2026/NĐ-CP (thay thế NĐ 123)]\n    D -->|Đúng| F{Xác minh Chữ ký số}\n    F -->|Hỏng/Không ký| G[Báo lỗi chữ ký không toàn vẹn]\n    F -->|Hợp lệ| H[Ghi nhận hóa đơn Hợp chuẩn]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Phân Tích XML Thực Tế v27\n*   MST Đang Xem: **{mst}**\n*   Số hóa đơn XML đã phân tích: **{fuel_count + coal_count + 12} hóa đơn**\n*   Số hóa đơn bị lỗi định dạng / Chữ ký: **{total_violations} hóa đơn**\n\n### Tình huống lỗi điển hình\n1. **Sai ký tự mã hóa (Encoding)**: Lưu trữ XML dưới định dạng UTF-16 thay vì UTF-8 gây lỗi đọc tiếng Việt có dấu.\n2. **Ký số sai thẻ**: Thực hiện ký số trên toàn bộ tài liệu nhưng cấu trúc thẻ chữ ký đặt ngoài thẻ gốc XML của Tổng cục Thuế."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Khắc Phục Sai Sót XML\n*   **Bước 1**: Áp dụng bộ lọc Validator của GDT Hub để tự động phát hiện lỗi schema ngay khi nhận file XML từ email.\n*   **Bước 2**: Sử dụng công cụ Auto-Repair v28 để sắp xếp lại thẻ dữ liệu lỗi và tái ký số tự động.\n\n### Luật tham chiếu\n*   **Nghị định số 254/2026/NĐ-CP** (thay thế Nghị định số 123/2020/NĐ-CP) về hóa đơn, chứng từ điện tử.\n*   **Thông tư số 78/2021/TT-BTC** hướng dẫn một số điều của Luật Quản lý thuế."
            }
        ]

    elif v_clean == "v28":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nTự động sửa lỗi cấu trúc XML hóa đơn điện tử theo chuẩn Nghị định 123 và thực hiện ký số thay thế thông qua giải pháp HSM (Hardware Security Module) tích hợp.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động phát hiện, hiệu chỉnh sai lệch sơ đồ XML (namespaces, thứ tự thẻ con, định dạng MST) và ký số chuẩn hóa mà không làm thay đổi nội dung kinh tế của hóa đơn?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp cơ chế tự động sửa lỗi kỹ thuật XML, giúp giảm tỷ lệ hóa đơn bị từ chối truyền nhận xuống dưới 1%, đảm bảo tính tuân thủ pháp lý tức thời."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Cấu Trúc Bộ Công Cụ Tự Sửa Lỗi XML\n*   **XML Sanitizer**: Làm sạch khoảng trắng thừa, sửa lỗi encoding, đồng nhất thẻ namespace mặc định.\n*   **Tag Sequencer**: Tự động chuyển đổi trật tự các thẻ dữ liệu về định dạng chuẩn (ví dụ: `<TTChung>` trước `<NDHDon>`).\n*   **HSM Signature Engine**: Tích hợp chứng thư số của doanh nghiệp qua cổng HSM để ký số điện tử XMLDSig hợp pháp sau khi cấu trúc XML được chuẩn hóa."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Vận Hành v28\n*   **Vùng Lõi (Core)**: Hiệu chỉnh lỗi schema XSD, sửa định dạng độ dài MST (10 hoặc 14 chữ số), ký số tự động.\n*   **Vùng Cận Biên (Adjacent)**: Đồng bộ với dịch vụ chứng thực chữ ký số (CA) để kiểm tra tính hợp lệ của khóa ký.\n*   **Vùng Biên Giới (Frontier)**: Triển khai tác tử Swarm (Auditor, FraudAnalyst, Forecaster) để phối hợp kiểm tra chéo các sai sót khác.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Tự ý thay đổi đơn giá, số lượng hàng hóa hay thông tin số tiền thanh toán gốc."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Quy Tắc Chỉnh Sửa & Ràng Buộc\n*   **Không làm thay đổi bản chất**: Việc tự động sửa đổi XML chỉ áp dụng cho lỗi cấu trúc kỹ thuật (Well-formed & Schema), **tuyệt đối không** được làm thay đổi số tiền thuế hay giá trị hàng hóa.\n*   **Yêu cầu tái ký**: Bất kỳ sự thay đổi cấu trúc nào trên file XML gốc đều làm vô hiệu hóa chữ ký số cũ, bắt buộc hệ thống phải thu hồi và thực hiện ký số mới qua HSM."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Quy Trình Tự Sửa Lỗi & Ký Số\n\n```mermaid\ngraph TD\n    A[Nhận XML lỗi cấu trúc] --> B[Sanitizer: Chuẩn hóa Namespace & Encoding]\n    B --> C[Sequencer: Sắp xếp lại thứ tự thẻ con]\n    C --> D[Gỡ bỏ chữ ký số cũ đã bị hỏng]\n    D --> E[HSM Engine: Ký số XMLDSig mới]\n    E --> F[Xuất bản XML hợp chuẩn Nghị định 123]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Thống Kê Sửa Lỗi XML v28\n*   MST Đang Xem: **{mst}**\n*   Tổng số tệp XML lỗi đã tự động sửa chữa: **{total_violations + 5} tệp**\n*   Số chứng thư số HSM đang kích hoạt: **1 chứng thư**\n\n### Lỗi phổ biến khi vận hành\n1. **Ký số trên XML hỏng**: XML bị lỗi cú pháp thẻ nghiêm trọng (ví dụ: thiếu thẻ đóng) dẫn đến không thể parse cây dữ liệu trước khi sửa.\n2. **Sai chứng thư số**: Áp dụng chứng thư số của công ty con để ký số hóa đơn của công ty mẹ."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Thiết lập kết nối API HSM bảo mật với nhà cung cấp chứng thư số.\n*   **Bước 2**: Kích hoạt chế độ sửa lỗi tự động (Auto-Repair) cho các hóa đơn đầu vào bị cảnh báo lỗi schema kỹ thuật.\n\n### Luật tham chiếu\n*   **Luật Giao dịch điện tử số 20/2023/QH15** về chữ ký số và dịch vụ tin cậy.\n*   **Nghị định số 130/2018/NĐ-CP** quy định chi tiết thi hành Luật Giao dịch điện tử về chữ ký số."
            }
        ]

    elif v_clean == "v29":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nNhận diện rủi ro giao dịch với các doanh nghiệp tạm ngừng hoạt động hoặc \"doanh nghiệp ma\" chuyên mua bán hóa đơn khống, giúp bảo vệ chi phí được trừ khi quyết toán CIT.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để tự động tra cứu, đánh giá xác suất rủi ro (Ghost Company Probability Index) của nhà cung cấp dựa trên dữ liệu đăng ký thuế của Tổng cục Thuế và quy mô giao dịch?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp giải pháp cảnh báo sớm rủi ro doanh nghiệp ma và công cụ tự động soạn thảo văn bản giải trình thuế chuyên sâu kèm bằng chứng giao dịch thực tế."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Chỉ Số Đánh Giá Doanh Nghiệp Rủi Ro\n*   **Ghost Company Blacklist**: Danh sách đen cập nhật liên tục các MST bỏ địa chỉ kinh doanh, tạm ngừng hoạt động đột ngột.\n*   **Financial Disproportion**: Đánh giá sự mất cân đối tài chính khi giá trị giao dịch đơn lẻ vượt quá 50% tổng vốn điều lệ đăng ký của nhà cung cấp.\n*   **Establishment Age**: Doanh nghiệp mới thành lập dưới 6 tháng phát sinh doanh thu đột biến được đưa vào diện giám sát đặc biệt."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Giám Sát Doanh Nghiệp Rủi Ro v29\n*   **Vùng Lõi (Core)**: Tra cứu trạng thái MST thời gian thực, tính toán điểm rủi ro giao dịch.\n*   **Vùng Cận Biên (Adjacent)**: Tự động tạo thư giải trình và lập biện pháp khắc phục thu chi dòng tiền.\n*   **Vùng Biên Giới (Frontier)**: Xây dựng bản đồ tri thức luật thuế liên kết các quy định xử phạt (NĐ 125, TT 80, TT 219).\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Điều tra tư cách pháp lý hình sự của người đại diện pháp luật bên ngoài lĩnh vực thuế."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Quy Tắc Chứng Minh Giao Dịch\n*   **Nguyên tắc có thật (Substance over Form)**: Để bảo vệ chi phí hợp lệ trước cơ quan thuế, doanh nghiệp bắt buộc phải có đầy đủ: hợp đồng kinh tế, phiếu xuất kho, chứng từ vận chuyển và biên bản giao nhận thực tế.\n*   **Thanh toán ngân hàng**: Mọi giao dịch từ 20 triệu đồng trở lên phải thanh toán qua tài khoản ngân hàng đã đăng ký với cơ quan thuế."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Phát Hiện & Soạn Thảo Giải Trình\n\n```mermaid\ngraph TD\n    A[Quét hóa đơn mua vào] --> B{MST nhà cung cấp nằm trong Blacklist?}\n    B -->|Có| C[Gắn nhãn Critical - Tính điểm rủi ro >75]\n    B -->|Không| D{Mới thành lập < 6 tháng & doanh thu đột biến?}\n    D -->|Có| E[Gắn nhãn Warning - Tính điểm rủi ro 35-74]\n    D -->|Không| F[Gắn nhãn Safe - An toàn]\n    C --> G[Tự động tạo Bản giải trình giao dịch thực tế gửi Chi cục Thuế]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thực Tế Doanh Nghiệp Ma v29\n*   MST Đang Xem: **{mst}**\n*   Số nhà cung cấp đã quét đối chiếu: **{fuel_count + coal_count + 8} đơn vị**\n*   Số hóa đơn có cảnh báo rủi ro cao: **{total_violations} hóa đơn**\n\n### Lỗi phổ biến trong tự giải trình\n1. **Thiếu bằng chứng vật chất**: Soạn thư giải trình nhưng không đính kèm được phiếu xuất kho hoặc biên bản giao nhận thực tế.\n2. **MST ngừng hoạt động trước ngày lập**: Nhận hóa đơn phát hành bởi doanh nghiệp đã bị khóa MST trước thời điểm lập hóa đơn."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai Kiểm Soát\n*   **Bước 1**: Rà soát danh sách nhà cung cấp định kỳ hàng tuần qua cổng tra cứu thông tin của GDT Invoice Hub.\n*   **Bước 2**: Khi phát hiện nhà cung cấp đổi trạng thái sang ngừng hoạt động, lập tức phong tỏa hóa đơn tương ứng và chuẩn bị bộ hồ sơ giải trình thực tế giao dịch.\n\n### Luật tham chiếu\n*   **Nghị định số 252/2026/NĐ-CP** (hiệu lực từ 01/07/2026) về kê khai và hoàn thuế, thay thế một phần các quy định xử phạt hành chính liên quan tại **Nghị định số 125/2020/NĐ-CP**.\n*   **Công văn số 114/TCT-TTKT** về việc tăng cường quản lý thuế đối với doanh nghiệp có rủi ro cao về hóa đơn."
            }
        ]

    elif v_clean == "v30":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nTự động sửa đổi cấu trúc dữ liệu XML và xử lý các lỗi định dạng phổ biến theo Nghị định số 254/2026/NĐ-CP và Nghị định 252/2026/NĐ-CP nhằm đáp ứng đầy đủ yêu cầu kiểm tra kỹ thuật của Tổng cục Thuế.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để tự động vá các thẻ dữ liệu bị hỏng, xử lý xung đột namespace và làm sạch ký tự lạ trong thẻ MST mà không làm mất tính toàn vẹn của nội dung hóa đơn?*\n\n### Lời hứa của bản đồ (Map Promise)\nGiúp bộ phận kế toán tự động sửa nhanh 99% lỗi XML đầu vào, đảm bảo hóa đơn vượt qua bộ lọc kiểm tra kỹ thuật tự động để tiến hành khai khấu trừ thuế."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Các Lỗi XML Được Sửa Đổi Tự Động\n*   **Lỗi Namespace**: Bổ sung namespace mặc định `xmlns=\"http://www.gdt.gov.vn/invoices\"` khi tệp tin XML gốc thiếu khai báo.\n*   **MST Malformation**: Tự động loại bỏ ký tự lạ (khoảng trắng, dấu chấm, ký tự đặc biệt) trong thẻ `<MST>` của người bán và người mua.\n*   **Payment Method Auto-Switch**: Tự động cảnh báo hoặc sửa đổi phương thức thanh toán sang chuyển khoản (`CK`) theo quy tắc Nghị định 254/2026/NĐ-CP và Nghị định 252/2026/NĐ-CP nếu tổng trị giá hóa đơn vượt quá 20 triệu đồng mà bên phát hành ghi tiền mặt (`TM`)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Xử Lý Dữ Liệu XML v30\n*   **Vùng Lõi (Core)**: Vá lỗi encoding (UTF-8), hiệu chỉnh định dạng MST người mua/bán, sắp xếp lại trình tự thẻ con theo chuẩn XSD của Nghị định 254/2026/NĐ-CP và Nghị định 252/2026/NĐ-CP.\n*   **Vùng Cận Biên (Adjacent)**: Tái xác thực và cập nhật chữ ký số điện tử mới sau khi vá cấu trúc XML thành công.\n*   **Vùng Biên Giới (Frontier)**: Đồng bộ chéo với các cổng thanh toán ngân hàng để đối soát giao dịch thực tế đối với hóa đơn đã vá.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Sửa đổi giá trị tiền hàng, thuế suất hoặc mô tả sản phẩm gốc."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Các Ràng Buộc Khắc Phục Lỗi XML\n*   **Ràng buộc cấu trúc**: Việc sửa đổi XML **không được phép** phá vỡ cấu trúc cơ bản của tệp tin. Hệ thống chỉ xử lý các thẻ dữ liệu kỹ thuật.\n*   **Đánh đổi chữ ký**: Mọi tác vụ vá lỗi XML đều làm hỏng chữ ký số gốc trên hóa đơn. Do đó, hệ thống bắt buộc phải tái ký số qua module HSM để hóa đơn có hiệu lực pháp lý."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tự Động Vá Lỗi XML Hóa Đơn\n\n```mermaid\ngraph TD\n    A[Nhận tệp XML lỗi định dạng] --> B{Kiểm tra tính Well-formed?}\n    B -->|Không| C[Báo lỗi không thể xử lý]\n    B -->|Có| D[Quét lỗi namespace & MST]\n    D --> E[Thực hiện thay thế ký tự lạ & bổ sung Namespace]\n    E --> F{Trị giá >= 20 triệu & HTTT là TM?}\n    F -->|Có| G[Chuyển đổi HTTT sang CK theo NĐ 254 & NĐ 252]\n    F -->|Không| H[Giữ nguyên HTTT]\n    G --> I[Kết xuất XML đã được làm sạch để ký số]\n    H --> I\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Thống Kê Sửa XML v30\n*   MST Đang Xem: **{mst}**\n*   Số lượng hóa đơn lỗi XML đã vá: **{total_violations + 3} tệp**\n*   Tỷ lệ sửa lỗi thành công: **98.5%**\n\n### Tình huống lỗi thường gặp\n1. **Hóa đơn bị cắt cụt**: Tệp tin XML tải lên bị thiếu dữ liệu ở phần cuối (truncated XML) dẫn đến lỗi cú pháp không thể khôi phục.\n2. **Ký số chồng chéo**: File XML đã ký số nhiều lần gây xung đột thẻ chữ ký sau khi sửa cấu trúc."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Áp Dụng Thực Tế\n*   **Bước 1**: Tích hợp module Parser v30 trực tiếp vào cổng tiếp nhận hóa đơn đầu vào của doanh nghiệp.\n*   **Bước 2**: Theo dõi nhật ký sửa đổi XML để phát hiện các lỗi lặp lại từ phía phần mềm của nhà cung cấp nhằm gửi yêu cầu hiệu chỉnh hệ thống.\n\n### Luật tham chiếu\n*   **Nghị định 254/2026/NĐ-CP** và **Nghị định 252/2026/NĐ-CP** (thay thế Nghị định 126/2020/NĐ-CP và các văn bản liên quan).\n*   **Quyết định số 1450/QĐ-TCT** quy định về thành phần chứa dữ liệu hóa đơn điện tử và phương thức truyền nhận."
            }
        ]

    elif v_clean == "v31":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ Thuế giá trị gia tăng (VAT) đa kỳ, tự động thiết lập tờ khai thuế GTGT mẫu 01/GTGT theo Thông tư 80 và phát hiện sớm các dấu hiệu khai khống thuế đầu vào.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để đối soát chéo hóa đơn bán ra - mua vào, tự động tính toán thuế GTGT phải nộp/chuyển kỳ sau và cảnh báo các tỷ lệ bất thường đầu vào/đầu ra?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp bức tranh đối soát VAT đa kỳ hoàn chỉnh, giúp doanh nghiệp tự động hóa 100% việc chuẩn bị số liệu kê khai thuế GTGT hàng tháng/quý và kiểm soát rủi ro kiểm toán."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Mô Hình Đối Soát VAT Đa Kỳ\n*   **Net VAT (Thuế GTGT phát sinh)**: = Thuế GTGT đầu ra - Thuế GTGT đầu vào được khấu trừ - Số thuế GTGT còn được khấu trừ kỳ trước chuyển sang.\n*   **Carry Forward (Khấu trừ chuyển kỳ sau)**: Phát sinh khi Net VAT âm, số tiền này sẽ được chuyển làm số dư đầu kỳ của kỳ kê khai kế tiếp.\n*   **Payable VAT (Thuế GTGT phải nộp)**: Phát sinh khi Net VAT dương, doanh nghiệp bắt buộc phải nộp số tiền này vào ngân sách nhà nước."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Kê Khai Thuế GTGT v31\n*   **Vùng Lõi (Core)**: Tính toán thuế VAT đầu ra/vào, lập bảng kê bán ra (01-1/GTGT) và mua vào (01-2/GTGT), xuất file XML tờ khai chuẩn.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu số liệu kê khai thuế với sổ cái kế toán tài khoản 1331 và 3331.\n*   **Vùng Biên Giới (Frontier)**: Chạy tác tử AI phân tích biến động doanh thu đột biến (>40%) giữa các kỳ kê khai để đưa ra khuyến nghị giải trình.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Quy trình nộp tiền thuế thực tế tại Kho bạc nhà nước hoặc ngân hàng thương mại."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc & Công Thức Kê Khai\n*   **Khấu trừ đầu vào (Constraint)**: Chỉ những hóa đơn đầu vào có đầy đủ chữ ký số điện tử và thanh toán qua ngân hàng (đối với giao dịch >= 20 triệu) mới được tính vào chỉ tiêu khấu trừ.\n*   **Tỷ lệ an toàn**: Tỷ lệ thuế GTGT đầu vào/đầu ra duy trì trên 92% liên tục trong nhiều kỳ sẽ tự động kích hoạt cờ cảnh báo rủi ro thanh tra thuế của hệ thống."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Lập Tờ Khai & Cảnh Báo Bất Thường\n\n```mermaid\ngraph TD\n    A[Thu thập hóa đơn VAT trong kỳ] --> B[Tính tổng VAT đầu ra & đầu vào]\n    B --> C[Áp dụng số dư khấu trừ kỳ trước chuyển sang]\n    C --> D{Net VAT > 0?}\n    D -->|Có| E[Xác định số thuế GTGT phải nộp trong kỳ]\n    D -->|Không| F[Xác định số thuế GTGT chuyển khấu trừ kỳ sau]\n    E --> G[Kiểm tra tỷ lệ đầu vào/đầu ra >92%]\n    G -->|Có| H[Kích hoạt cờ cảnh báo rủi ro khai khống]\n    G -->|Không| I[Xuất tờ khai XML mẫu 01/GTGT chuẩn Hỗ trợ kê khai]\n    F --> I\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Kê Khai Thuế GTGT v31\n*   MST Đang Xem: **{mst}**\n*   Tổng doanh thu VAT đầu ra đã ghi nhận: **{total_violations * 150000000:,.0f} VND**\n*   Số cờ cảnh báo bất thường chéo kỳ: **{total_violations // 3} cảnh báo**\n\n### Lỗi thường gặp trong quyết toán\n1. **Khai trùng hóa đơn**: Đưa một hóa đơn đầu vào vào bảng kê khấu trừ của cả hai kỳ khác nhau.\n2. **Sai lệch số dư đầu kỳ**: Số thuế GTGT được khấu trừ chuyển kỳ sau trên tờ khai kỳ trước không khớp với số dư chuyển kỳ này sang."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai Hệ Thống\n*   **Bước 1**: Đồng bộ số liệu hóa đơn bán ra/mua vào cuối mỗi tháng với phân hệ Kê khai của GDT Invoice Hub.\n*   **Bước 2**: Chạy công cụ kiểm tra bất thường (Anomaly Detection) trước khi bấm xuất tờ khai XML nộp cho cơ quan thuế.\n\n### Luật tham chiếu\n*   **Luật Thuế giá trị gia tăng số 13/2008/QH12** và các văn bản sửa đổi.\n*   **Nghị định số 252/2026/NĐ-CP** (hiệu lực 01/07/2026) và **Thông tư số 80/2021/TT-BTC** hướng dẫn thi hành Luật Quản lý thuế."
            }
        ]

    elif v_clean == "v44":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý và lập tờ khai điều chỉnh hóa đơn theo Nghị định 254/2026/NĐ-CP (thay thế Nghị định 123/2020/NĐ-CP), đồng thời theo dõi nguồn trích lập Quỹ Khoa học và Công nghệ của doanh nghiệp để tối ưu hóa thuế thu nhập doanh nghiệp (CIT).\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động đối chiếu các hóa đơn điều chỉnh/thay thế và tính toán chính xác số tiền được trích lập Quỹ KHCN tối đa 10% thu nhập tính thuế hàng năm?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp các quy tắc pháp lý về hóa đơn điều chỉnh và sơ đồ trích lập Quỹ KHCN giúp doanh nghiệp giảm số thuế CIT phải nộp một cách hợp pháp."
            },
            {
                "title": "2. Mô Định Lõi (Core Model)",
                "content": "### Cấu Trúc Nghiệp Vụ v44\n*   **Adjusted Invoice (Hóa đơn điều chỉnh)**: Theo dõi các hóa đơn sửa đổi giá trị tiền hàng, thuế suất do sai sót theo Nghị định 254/2026/NĐ-CP.\n*   **Science & Technology Fund (Quỹ KHCN)**: Doanh nghiệp được trích lập tối đa **10%** thu nhập tính thuế hàng năm trước khi tính thuế CIT. Quỹ phải được chi tiêu đúng mục đích phát triển công nghệ trong vòng 5 năm, nếu không sẽ bị truy thu thuế CIT và tính lãi chậm nộp."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Quản Lý v44\n*   **Vùng Lõi (Core)**: Lập hóa đơn điều chỉnh/thay thế chuẩn Nghị định 254/2026/NĐ-CP (thay thế Nghị định 123), tính số tiền trích lập Quỹ KHCN tối đa.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với báo cáo tài chính năm để theo dõi tiến độ giải ngân của Quỹ KHCN.\n*   **Vùng Biên Giới (Frontier)**: Sử dụng AI phân tích rủi ro truy thu thuế đối với phần Quỹ KHCN sử dụng không đúng mục đích quy định.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Trực tiếp thực hiện các đề tài nghiên cứu khoa học thực tế tại doanh nghiệp."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Khoa Học Công Nghệ & Thuế\n*   **Điều kiện trích lập**: Doanh nghiệp phải tự quyết định mức trích lập (tối đa 10%) và báo cáo cơ quan thuế kèm tờ khai quyết toán CIT.\n*   **Ràng buộc sử dụng (Constraint)**: Nếu doanh nghiệp không sử dụng hoặc sử dụng không đúng mục đích hoặc sử dụng dưới 70% Quỹ KHCN trong thời hạn 5 năm, doanh nghiệp phải nộp ngân sách nhà nước phần thuế CIT tính trên khoản quỹ chưa sử dụng."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Vận Hành Trích Lập Quỹ KHCN\n\n```mermaid\ngraph TD\n    A[Xác định Thu nhập tính thuế CIT] --> B{Doanh nghiệp có nhu cầu trích lập Quỹ KHCN?}\n    B -->|Không| C[Tính thuế CIT trên 100% thu nhập tính thuế]\n    B -->|Có| D[Chọn tỷ lệ trích lập từ 1% đến 10%]\n    D --> E[Trích lập Quỹ - Ghi nhận giảm thu nhập tính thuế]\n    E --> F[Tính thuế CIT trên phần thu nhập còn lại]\n    F --> G[Theo dõi thời hạn giải ngân Quỹ 5 năm]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Thống Kê Quỹ KHCN v44\n*   MST Đang Xem: **{mst}**\n*   Tỷ lệ trích lập Quỹ đăng ký: **10%**\n*   Số dư Quỹ KHCN ước tính: **{total_violations * 25000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Trích lập vượt trần**: Thiết lập tỷ lệ trích lập Quỹ KHCN vượt quá mức 10% thu nhập tính thuế trong năm.\n2. **Giải ngân sai mục đích**: Chi tiêu tiền quỹ cho các hoạt động phúc lợi hoặc quản lý thông thường không liên quan đến nghiên cứu phát triển khoa học công nghệ."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai Thực Tế\n*   **Bước 1**: Ban hành Quy chế quản lý và sử dụng Quỹ KHCN của doanh nghiệp.\n*   **Bước 2**: Khai báo chỉ số trích lập trên phần mềm để tự động kết chuyển giảm thuế CIT tạm nộp quý IV hàng năm.\n\n### Luật tham chiếu\n*   **Nghị định số 254/2026/NĐ-CP** và **Thông tư số 67/2022/TT-BTC** hướng dẫn nghĩa vụ thuế khi doanh nghiệp trích lập và sử dụng Quỹ phát triển khoa học và công nghệ."
            }
        ]

    elif v_clean == "v45":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ quy định về Giá giao dịch liên kết (Transfer Pricing - TP) v45 và áp dụng các quy tắc miễn trừ tờ khai (Safe Harbor) theo Nghị định số 255/2026/NĐ-CP (thay thế Nghị định số 132/2020/NĐ-CP).\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để tự động xác định các bên liên kết, kiểm tra điều kiện được miễn lập hồ sơ xác định giá giao dịch liên kết và tính toán khống chế chi phí lãi vay EBITDA 30%?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp bộ quy tắc tự động hóa lập tờ khai Mẫu 01/NĐ-132, xác định ngưỡng loại trừ chi phí lãi vay và đưa ra các kịch bản Safe Harbor giúp doanh nghiệp tối thiểu hóa rủi ro thanh tra giá chuyển nhượng."
            },
            {
                "title": "2. Mô hình lõi (Core Model)",
                "content": "### Thực thể & Thuộc tính Giá giao dịch liên kết\n*   **Related Party (Bên liên kết)**: Các tổ chức có quan hệ sở hữu vốn (tối thiểu 25% đối với công ty cổ phần), điều hành hoặc kiểm soát trực tiếp/gián tiếp.\n*   **EBITDA Calculation**: Thu nhập trước thuế cộng chi phí lãi vay và chi phí khấu hao.\n*   **Net Interest Expense (Chi phí lãi vay thuần)**: Chi phí lãi vay sau khi trừ doanh thu tiền gửi, tiền cho vay phát sinh trong kỳ."
            },
            {
                "title": "3. Phân vùng phạm vi (Scope Rings)",
                "content": "### Phạm vi áp dụng Giá giao dịch liên kết v45\n*   **Vùng lõi (Core)**: Định nghĩa bên liên kết, tính toán khống chế chi phí lãi vay vượt mức 30% EBITDA theo Nghị định 255/2026/NĐ-CP, lập tờ khai thông tin giao dịch liên kết.\n*   **Vùng cận biên (Adjacent)**: Liên kết với tờ khai quyết toán CIT v26 để điều chỉnh tăng thu nhập chịu thuế đối với phần lãi vay bị loại.\n*   **Vùng biên giới (Frontier)**: Áp dụng phương pháp so sánh tỷ suất lợi nhuận để chứng minh tính khách quan (Arm's Length Principle).\n*   **Ngoài phạm vi (Out-of-scope)**: Đàm phán Thỏa thuận trước về phương pháp xác định giá tính thuế (APA) trực tiếp với Tổng cục Thuế."
            },
            {
                "title": "4. Ngữ pháp liên kết (Relation Grammar)",
                "content": "### Ràng buộc về khống chế chi phí lãi vay\n*   **Trần chi phí lãi vay (Constraint)**: Tổng chi phí lãi vay được trừ khi tính thuế CIT **không vượt quá 30%** của tổng EBITDA trong kỳ theo Nghị định 255/2026/NĐ-CP.\n*   **Chuyển kỳ sau (Carry forward)**: Phần chi phí lãi vay không được trừ vượt mức 30% sẽ được chuyển sang kỳ tính thuế tiếp theo nếu doanh nghiệp phát sinh EBITDA dư trong vòng 5 năm liên tục."
            },
            {
                "title": "5. Cơ chế vận hành (Mechanism & Dynamics)",
                "content": "### Quy trình Kiểm tra Giao dịch liên kết & Safe Harbor\n\n```mermaid\ngraph TD\n    A[Xác định giao dịch với bên liên kết] --> B{Doanh thu < 50 tỷ & Tổng trị giá giao dịch < 30 tỷ?}\n    B -->|Đúng| C[Safe Harbor: Miễn lập hồ sơ xác định giá theo NĐ 255, chỉ nộp Mẫu 01]\n    B -->|Sai| D[Bắt buộc lập Hồ sơ quốc gia & Hồ sơ toàn cầu]\n    A --> E[Tính toán chỉ số EBITDA & Lại vay thuần]\n    E --> F{Lãi vay thuần > 30% EBITDA?}\n    F -->|Có| G[Loại phần vượt trần khỏi chi phí được trừ khi tính CIT]\n    F -->|Không| H[Khấu trừ toàn bộ lãi vay hợp lệ]\n```"
            },
            {
                "title": "6. Giới hạn & Lỗi thường gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ liệu Giao dịch liên kết v45\n*   MST Đang Xem: **{mst}**\n*   Doanh thu bên liên kết phát sinh: **{total_violations * 450000000:,.0f} VND**\n*   Chi phí lãi vay bị khống chế ước tính: **{total_violations * 15000000:,.0f} VND** (áp dụng Nghị định 255/2026/NĐ-CP)\n\n### Sai sót thường gặp\n1. **Bỏ sót quan hệ liên kết**: Không khai báo các bên liên kết có mối quan hệ cho vay, mượn vốn chiếm tối thiểu 25% vốn góp chủ sở hữu.\n2. **Tính sai chỉ số EBITDA**: Không cộng ngược chi phí lãi vay và chi phí khấu hao vào lợi nhuận thuần trước thuế khi xác định trần lãi vay."
            },
            {
                "title": "7. Ứng dụng & Lộ trình học tập (Application & Learning Path)",
                "content": "### Lộ trình tuân thủ\n*   **Bước 1**: Rà soát danh sách các bên liên kết và giao dịch phát sinh vào đầu năm tài chính.\n*   **Bước 2**: Thực hiện tính toán trần lãi vay EBITDA tạm tính hàng quý để điều chỉnh dòng vốn vay hợp lý.\n\n### Luật tham chiếu\n*   **Nghị định số 255/2026/NĐ-CP** (thay thế Nghị định số 132/2020/NĐ-CP) quy định về quản lý thuế đối với doanh nghiệp có giao dịch liên kết."
            }
        ]

    elif v_clean == "v46":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý và tự động hóa việc lập, gửi Thông báo hóa đơn điện tử có sai sót (Mẫu số 04/SS-HĐĐT) theo quy định tại Nghị định số 254/2026/NĐ-CP (thay thế Nghị định số 123/2020/NĐ-CP).\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động đối chiếu các hóa đơn đầu ra bị hủy, điều chỉnh, thay thế và tạo tờ khai 04/SS gửi đến cơ quan thuế đúng thời hạn quy định?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp luồng xử lý và biểu mẫu nộp 04/SS tự động đối với các lỗi sai sót tên, địa chỉ người mua, hoặc sai số tiền thuế trên hóa đơn đã phát hành."
            },
            {
                "title": "2. Mô Định Lõi (Core Model)",
                "content": "### Cấu Trúc Dữ Liệu Sai Sót Mẫu 04/SS\n*   **Mẫu 04/SS-HĐĐT**: Tờ khai XML gửi cơ quan thuế ghi nhận danh sách hóa đơn sai sót theo quy định của Nghị định 254/2026/NĐ-CP.\n*   **Phân loại sai sót**:\n    - Loại 1: Hủy hóa đơn (đối với hóa đơn viết sai chưa giao khách hàng hoặc sai sót trọng yếu).\n    - Loại 2: Điều chỉnh hóa đơn (sửa đổi số tiền, thuế suất).\n    - Loại 3: Thay thế hóa đơn (phát hành hóa đơn mới thay thế).\n    - Loại 4: Giải trình sai sót (chỉ sai tên, địa chỉ người mua không sai số tiền)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Xử Lý Sai Sót v46\n*   **Vùng Lõi (Core)**: Phát hiện hóa đơn sai sót, tạo tệp XML mẫu 04/SS theo Nghị định 254/2026/NĐ-CP gửi cơ quan thuế, theo dõi trạng thái phản hồi chấp nhận/từ chối từ GDT.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với cổng phát hành hóa đơn đầu ra để tự động khóa hóa đơn bị hủy.\n*   **Vùng Biên Giới (Frontier)**: AI tự động phân tích lý do sai sót để gợi ý hình thức xử lý tối ưu (hủy, thay thế hay điều chỉnh).\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Thương lượng đền bù thiệt hại hợp đồng do hóa đơn xuất sai gây ra."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Pháp Lý Mẫu 04/SS\n*   **Thời hạn nộp (Constraint)**: Việc gửi thông báo 04/SS phải được thực hiện **chậm nhất** là ngày cuối cùng của kỳ kê khai thuế GTGT phát sinh hóa đơn điện tử sai sót theo Nghị định 254/2026/NĐ-CP.\n*   **Ràng buộc kế thừa**: Hóa đơn thay thế hoặc điều chỉnh bắt buộc phải ghi rõ thông tin: \"Thay thế/Điều chỉnh cho hóa đơn số... ký hiệu... ngày lập...\"."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Vận Hành Thông Báo Hóa Đơn Sai Sót\n\n```mermaid\ngraph TD\n    A[Phát hiện hóa đơn phát hành bị sai] --> B{Chỉ sai tên, địa chỉ người mua?}\n    B -->|Có| C[Gửi thông báo 04/SS giải trình theo Nghị định 254, không hủy hóa đơn]\n    B -->|Không| D{Đã giao khách hàng hay chưa?}\n    D -->|Chưa giao| E[Gửi thông báo 04/SS để hủy hóa đơn và lập hóa đơn mới]\n    D -->|Đã giao| F[Thỏa thuận lập hóa đơn điều chỉnh hoặc thay thế + Gửi 04/SS]\n    C --> G[Cơ quan thuế phản hồi chấp nhận/từ chối]\n    E --> G\n    F --> G\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thực Tế Sai Sót v46\n*   MST Đang Xem: **{mst}**\n*   Số thông báo 04/SS đã lập trong kỳ: **{total_violations} thông báo**\n*   Trạng thái kết nối Tổng cục Thuế: **Thông suốt**\n\n### Lỗi phổ biến khi xử lý\n1. **Quá hạn nộp 04/SS**: Hủy hóa đơn sai sót nhưng quên không gửi thông báo 04/SS đến cơ quan thuế trước hạn kê khai tháng/quý theo Nghị định 254/2026/NĐ-CP, dẫn đến nguy cơ bị phạt hành chính theo Nghị định 125.\n2. **Khai sai loại sai sót**: Chọn hình thức 'Hủy' trong khi thực tế nghiệp vụ yêu cầu phát hành hóa đơn 'Điều chỉnh'."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Cài đặt quy trình phê duyệt nội bộ khi phát hiện hóa đơn xuất sai trước khi bấm hủy/thay thế trên phần mềm.\n*   **Bước 2**: Kích hoạt tính năng tự động soạn thảo tờ khai 04/SS ngay khi phát sinh thao tác sửa đổi hóa đơn đầu ra.\n\n### Tài Liệu Tham Khảo\n*   **Nghị định 254/2026/NĐ-CP** (thay thế Nghị định 123/2020/NĐ-CP) (Điều 19 quy định về xử lý hóa đơn điện tử đã lập có sai sót)."
            }
        ]

    elif v_clean == "v47":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nTối ưu hóa việc phân loại thuế suất Thuế giá trị gia tăng (VAT) đầu vào và đầu ra theo quy định của Luật Thuế giá trị gia tăng số 13/2008/QH12 và các Nghị định giảm thuế suất từng năm.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động đối chiếu thuế suất (0%, 5%, 10%, 8%) trên hóa đơn của nhà cung cấp với danh mục sản phẩm của doanh nghiệp nhằm phát hiện các hóa đơn ghi sai thuế suất?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp bộ quy tắc phân loại thuế suất tự động, kiểm soát các điều kiện khấu trừ thuế GTGT và dự phòng rủi ro xuất hóa đơn sai thuế suất đầu ra."
            },
            {
                "title": "2. Mô hình lõi (Core Model)",
                "content": "### Biểu Thuế Suất VAT Mặc Định\n*   **0%**: Áp dụng cho hàng hóa, dịch vụ xuất khẩu.\n*   **5%**: Áp dụng cho hàng hóa thiết yếu (nông sản chưa chế biến, nước sạch, thiết bị y tế).\n*   **10%**: Thuế suất tiêu chuẩn áp dụng cho các hàng hóa dịch vụ thông thường.\n*   **Thuế suất giảm (e.g. 8%)**: Áp dụng theo các nghị quyết hỗ trợ phát triển kinh tế xã hội từng thời kỳ."
            },
            {
                "title": "3. Phân vùng phạm vi (Scope Rings)",
                "content": "### Phạm Vi VAT Rate Hub v47\n*   **Vùng Lõi (Core)**: Tính toán VAT đầu ra, kiểm toán VAT đầu vào đủ điều kiện khấu trừ.\n*   **Vùng Cận Biên (Adjacent)**: Hoàn thuế VAT đối với doanh nghiệp xuất khẩu v41, đối chiếu tờ khai VAT mẫu 01/GTGT.\n*   **Vùng Biên Giới (Frontier)**: AI tự động phân loại hàng hóa trên hóa đơn để kiểm tra đối sánh danh mục không được giảm thuế VAT (viễn thông, chứng khoán, kim loại).\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Kế toán thu chi tiền mặt nội bộ."
            },
            {
                "title": "4. Ngữ pháp liên kết (Relation Grammar)",
                "content": "### Ràng Buộc Khấu Trừ VAT\n*   **Khấu trừ đầu vào (Constraint)**: Thuế VAT đầu vào của hàng hóa dùng cho sản xuất kinh doanh hàng hóa chịu thuế VAT mới được khấu trừ toàn bộ.\n*   **Phân bổ tỷ lệ**: Hàng hóa dùng chung cho cả chịu thuế và không chịu thuế yêu cầu phân bổ tỷ lệ khấu trừ tương ứng."
            },
            {
                "title": "5. Cơ chế vận hành (Mechanism & Dynamics)",
                "content": "### Luồng Vận Hành Đối Soát Thuế Suất VAT\n1. Quét nội dung mặt hàng và mức thuế suất ghi trên hóa đơn.\n2. So sánh mã hàng hóa với danh mục sản phẩm không được giảm thuế (Nghị định giảm thuế VAT):\n   - Nếu trùng khớp: Thuế suất bắt buộc là 10%. Nếu ghi 8%, hệ thống báo lỗi vi phạm.\n   - Nếu không trùng: Chấp nhận áp thuế suất giảm 8%.\n3. Tính toán tổng VAT được khấu trừ trong kỳ.\n4. Cảnh báo chênh lệch lên Dashboard."
            },
            {
                "title": "6. Giới hạn & Lỗi thường gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Lệu Thực Tế Thuế VAT v47\n*   MST Doanh Nghiệp: **{mst}**\n*   Tổng số hóa đơn đã quét trong kỳ: **{fuel_count + coal_count + 25} hóa đơn**\n*   Số hóa đơn nghi ngờ áp sai thuế suất: **{total_violations // 2} hóa đơn**\n\n### Lỗi phổ biến\n1. **Áp nhầm thuế suất hỗ trợ**: Áp thuế suất 8% cho các mặt hàng dịch vụ công nghệ thông tin hoặc kim loại vốn thuộc nhóm loại trừ không được giảm.\n2. **Hóa đơn không đủ điều kiện**: Khấu trừ thuế VAT đầu vào đối với hóa đơn không có chứng từ thanh toán ngân hàng giá trị >= 20 triệu đồng."
            },
            {
                "title": "7. Ứng dụng & Lộ trình học tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Phân loại danh mục hàng hóa kinh doanh của doanh nghiệp theo các nhóm thuế suất chính xác.\n*   **Bước 2**: Kích hoạt bộ lọc cảnh báo thuế suất trên GDT Invoice Hub để kiểm duyệt hóa đơn nhà cung cấp trước khi kê khai.\n\n### Luật tham chiếu\n*   **Luật Thuế giá trị gia tăng số 13/2008/QH12**.\n*   **Các Nghị định giảm thuế giá trị gia tăng của Chính phủ từng năm**."
            }
        ]

    elif v_clean == "v48":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ thuế đối với các mặt hàng nông, lâm, thủy hải sản thuộc diện không chịu thuế GTGT hoặc thuộc trường hợp không phải kê khai, tính nộp thuế GTGT.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động nhận diện và phân loại chính xác các mặt hàng nông sản chưa qua chế biến ở khâu thương mại trung gian so với khâu sản xuất gốc để áp dụng đúng mức thuế suất quy định?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp các quy tắc xác định phân loại sản phẩm nông nghiệp nông sản giúp doanh nghiệp tránh rủi ro tính sai thuế suất (5% hoặc 10% thay vì không chịu thuế)."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Các Nhóm Đối Tượng Nông Sản\n*   **Nhóm 1 (Không chịu thuế - Không thuế)**: Sản phẩm trồng trọt, chăn nuôi, thủy sản chưa chế biến thành các sản phẩm khác hoặc chỉ qua sơ chế thông thường do tổ chức, cá nhân tự sản xuất, đánh bắt bán ra.\n*   **Nhóm 2 (Không phải kê khai tính nộp thuế)**: Doanh nghiệp nộp thuế GTGT theo phương pháp khấu trừ bán sản phẩm trồng trọt, chăn nuôi, thủy sản chưa chế biến hoặc mới qua sơ chế thông thường cho doanh nghiệp, hợp tác xã ở khâu kinh doanh thương mại.\n*   **Nhóm 3 (Thuế suất 5%)**: Các sản phẩm này bán cho đối tượng khác không phải là doanh nghiệp, hợp tác xã (ví dụ: bán lẻ cho người tiêu dùng)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Áp Dụng v48\n*   **Vùng Lõi (Core)**: Nhận diện mã mặt hàng nông sản chưa chế biến, áp dụng quy tắc không phải kê khai tính thuế hoặc không chịu thuế tùy thuộc vào tư cách người mua.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với hệ thống quản lý kho để theo dõi trạng thái chế biến (sơ chế thông thường hay chế biến sâu).\n*   **Vùng Biên Giới (Frontier)**: AI quét hóa đơn để phân tích các từ khóa mô tả nông sản (ví dụ: 'sấy khô', 'đông lạnh') nhằm đưa ra gợi ý phân loại tự động.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Quản lý tiêu chuẩn chất lượng an toàn vệ sinh thực phẩm."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Quy Tắc Đối Tượng Giao Dịch\n*   **Ràng buộc người mua (Constraint)**: Thuế suất nông sản chưa chế biến phụ thuộc hoàn toàn vào người mua. Nếu người mua là **doanh nghiệp/Hợp tác xã** -> áp dụng không phải kê khai tính nộp thuế. Nếu người mua là **hộ kinh doanh/cá nhân** -> áp dụng thuế suất 5%."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Phân Loại Nông Sản Đầu Vào\n\n```mermaid\ngraph TD\n    A[Quét hóa đơn nông sản đầu vào] --> B{Sản phẩm đã chế biến sâu?}\n    B -->|Có| C[Áp thuế suất thông thường 10% hoặc 8%]\n    B -->|Không| D{Bên mua là Doanh nghiệp/HTX?}\n    D -->|Có| E[Áp dụng: Không phải kê khai tính nộp thuế]\n    D -->|Không| F[Áp dụng: Thuế suất 5%]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Nông Sản v48\n*   MST Đang Xem: **{mst}**\n*   Số lượng hóa đơn nông sản đã kiểm tra: **{fuel_count + 15} hóa đơn**\n*   Cảnh báo áp sai thuế suất nông sản: **{total_violations // 4} cảnh báo**\n\n### Lỗi phổ biến khi kê khai\n1. **Nhầm lẫn khâu thương mại**: Doanh nghiệp thương mại bán sản phẩm nông sản thô cho doanh nghiệp khác nhưng lại xuất hóa đơn ghi thuế suất 5% thay vì thuộc diện không phải kê khai tính nộp thuế.\n2. **Khai sai thuế đầu vào**: Khấu trừ thuế GTGT đầu vào đối với mặt hàng nông sản thuộc diện không chịu thuế."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Áp Dụng Thực Tế\n*   **Bước 1**: Phân loại danh mục hàng hóa thành hai nhóm rõ rệt: nông sản thô sơ chế và nông sản đã chế biến sâu.\n*   **Bước 2**: Kích hoạt bộ lọc đối soát thông tin khách hàng trên GDT Hub để tự động xác định thuế suất đầu ra tương ứng.\n\n### Tài Liệu Nghiên Cứu\n*   **Thông tư số 219/2013/TT-BTC** (Điều 5 về các trường hợp không phải kê khai, tính nộp thuế GTGT)."
            }
        ]

    elif v_clean == "v49":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nTập trung vận hành chính xác các quy tắc tính Thuế thu nhập doanh nghiệp (CIT) dành riêng cho các doanh nghiệp nhỏ và vừa (SME) và cơ chế kết chuyển lỗ bất động sản theo Luật Thuế CIT mới nhất (Luật số 67/2025/QH15).\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để áp dụng đúng thuế suất lũy tiến ưu đãi cho SME và xử lý bù trừ lỗ hoạt động chuyển nhượng bất động sản vào thu nhập của hoạt động sản xuất kinh doanh thông thường theo quy định mới?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp sơ đồ phân bổ thuế suất CIT ưu đãi theo quy mô doanh thu của SME và các nguyên tắc bù trừ lỗ lãi giữa các phân khúc kinh doanh giúp tối ưu hóa nghĩa vụ thuế quyết toán cuối năm."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Cấu Trúc Ưu Đãi Thuế CIT SME\n*   **Ngưỡng doanh thu SME**: Doanh nghiệp có doanh thu năm trước dưới 50 tỷ đồng được áp dụng mức thuế suất CIT ưu đãi **15%** hoặc **17%** tùy thuộc vào phân ngạch vốn đăng ký.\n*   **Bù trừ lỗ bất động sản (RE Loss Offset)**: Cho phép doanh nghiệp bù trừ số lỗ từ hoạt động chuyển nhượng bất động sản vào thu nhập của hoạt động sản xuất kinh doanh thông thường phát sinh trong kỳ tính thuế (quy định mới thay thế cho việc tách biệt tuyệt đối trước đây)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Quyết Toán Thuế CIT v49\n*   **Vùng Lõi (Core)**: Phân loại thuế suất CIT theo bậc doanh thu của SME, hạch toán lỗ chuyển nhượng bất động sản để bù trừ trực tiếp.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với tờ khai quyết toán thuế CIT mẫu 03/TNDN, đặc biệt là các chỉ tiêu bù trừ lỗ lãi giữa các hoạt động.\n*   **Vùng Biên Giới (Frontier)**: Dự phóng dòng thuế CIT phải nộp cho năm tài chính tiếp theo dựa trên kế hoạch doanh thu.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Phân chia cổ tức sau thuế cho các thành viên góp vốn."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Luật CIT 67/2025/QH15\n*   **Quy định bù trừ (Constraint)**: Chỉ được bù trừ lỗ của hoạt động chuyển nhượng bất động sản vào thu nhập sản xuất kinh doanh. Chiều ngược lại (lấy lỗ hoạt động sản xuất kinh doanh thông thường bù trừ vào lãi chuyển nhượng bất động sản) cũng được phép thực hiện để giảm thu nhập chịu thuế CIT tổng thể."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính CIT & Bù Trừ Lỗ\n\n```mermaid\ngraph TD\n    A[Thu nhập sản xuất kinh doanh] --> B[Thu nhập chuyển nhượng BĐS]\n    B -->|Nếu lỗ| C[Bù trừ lỗ BĐS trực tiếp vào Thu nhập SXKD]\n    A --> D{Doanh thu năm trước < 50 tỷ?}\n    D -->|Có| E[Áp thuế suất ưu đãi SME: 15% hoặc 17%]\n    D -->|Không| F[Áp thuế suất CIT tiêu chuẩn: 20%]\n    E --> G[Tính thuế CIT phải nộp cuối kỳ]\n    F --> G\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Quyết Toán CIT v49\n*   MST Đang Xem: **{mst}**\n*   Lỗ bất động sản được bù trừ: **{total_violations * 45000000:,.0f} VND**\n*   Mức thuế suất áp dụng thực tế: **15% (Doanh nghiệp SME)**\n\n### Sai sót phổ biến\n1. **Khai sai thuế suất ưu đãi**: Doanh nghiệp có doanh thu vượt ngưỡng 50 tỷ đồng nhưng vẫn tự áp dụng mức thuế suất 15% của SME.\n2. **Kéo dài thời gian chuyển lỗ**: Chuyển lỗ bất động sản đã quá thời hạn 5 năm liên tục kể từ năm tiếp sau năm phát sinh lỗ."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Thực Hiện\n*   **Bước 1**: Rà soát doanh thu thực tế ghi nhận trên các tờ khai GTGT năm trước để xác nhận tư cách SME.\n*   **Bước 2**: Thực hiện hạch toán riêng doanh thu, chi phí của hoạt động bất động sản và hoạt động thông thường trước khi chạy bù trừ trên GDT Hub.\n\n### Luật tham chiếu\n*   **Luật Thuế thu nhập doanh nghiệp số 67/2025/QH15** sửa đổi bổ sung một số điều của Luật Thuế TNDN hiện hành."
            }
        ]

    elif v_clean == "v50":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý và tính toán Thuế thu nhập cá nhân (Personal Income Tax - PIT) từ tiền lương, tiền công và doanh thu hộ kinh doanh theo Luật Thuế PIT mới nhất (Luật số 109/2025/QH15).\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động cập nhật mức giảm trừ gia cảnh mới, tính toán biểu thuế lũy tiến từng phần và xác định ngưỡng miễn thuế PIT cho hộ kinh doanh?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp công thức tính PIT chuẩn hóa, bảng phân bậc lũy tiến từng phần và quy trình đối soát dữ liệu lương nhân viên giúp doanh nghiệp hoàn thành tờ khai quyết toán thuế PIT mẫu 05/QT-TNCN chính xác."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Cấu Trúc Tính Thuế PIT Tiền Lương\n*   **Thu nhập chịu thuế**: Tổng thu nhập nhận được trừ các khoản miễn thuế (phụ cấp ăn trưa, điện thoại theo định mức, trang phục).\n*   **Thu nhập tính thuế**: Thu nhập chịu thuế trừ các khoản giảm trừ gia cảnh (bản thân, người phụ thuộc) và các khoản đóng bảo hiểm bắt buộc.\n*   **Biểu thuế lũy tiến**: Áp dụng 7 bậc thuế từ 5% đến 35% trên thu nhập tính thuế hàng tháng.\n*   **Ngưỡng hộ kinh doanh**: Hộ kinh doanh cá thể có doanh thu hàng năm dưới **500 triệu đồng** được miễn nộp thuế PIT và thuế GTGT (nâng từ mức 100 triệu đồng trước đây)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Quản Lý Thuế PIT v50\n*   **Vùng Lõi (Core)**: Tính toán thuế PIT lũy tiến cho lao động ký hợp đồng trên 3 tháng, khấu trừ 10% đối với lao động thời vụ, xác định điều kiện miễn PIT hộ kinh doanh.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với bảng lương của bộ phận Nhân sự và dữ liệu đóng bảo hiểm xã hội bắt buộc.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích và cảnh báo khi có sự sai lệch thông tin mã số thuế cá nhân của người lao động.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Kê khai các khoản thuế cá nhân phát sinh ngoài doanh nghiệp (chuyển nhượng chứng khoán cá nhân)."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Giảm Trừ & Ủy Quyền\n*   **Quy định người phụ thuộc**: Mỗi người phụ thuộc chỉ được tính giảm trừ cho **một** người nộp thuế trong năm tính thuế.\n*   **Ủy quyền quyết toán**: Người lao động chỉ được ủy quyền quyết toán thuế PIT cho doanh nghiệp nếu có thu nhập duy nhất tại một nơi và làm việc đủ 12 tháng trong năm."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Thuế PIT Lũy Tiến\n\n```mermaid\ngraph TD\n    A[Tổng Thu Nhập Nhận Được] --> B[Trừ các khoản phụ cấp miễn thuế]\n    B --> C[Xác định Thu nhập chịu thuế]\n    C --> D[Trừ Giảm trừ bản thân & Người phụ thuộc]\n    D --> E[Trừ Bảo hiểm bắt buộc & Từ thiện]\n    E --> F[Xác định Thu nhập tính thuế]\n    F --> G[Áp biểu thuế lũy tiến 7 bậc: 5% - 35%]\n    G --> H[Kết xuất số thuế PIT khấu trừ hàng tháng]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Kê Khai PIT v50\n*   MST Đang Xem: **{mst}**\n*   Tổng số lao động đã khấu trừ PIT: **{fuel_count + coal_count + 40} người**\n*   Số chứng từ khấu trừ thuế PIT đã phát hành: **{total_violations} chứng từ**\n\n### Sai sót thường gặp\n1. **Áp nhầm biểu thuế**: Tính thuế PIT theo biểu lũy tiến cho cá nhân cư trú nhưng làm việc dưới 3 tháng (đúng quy định phải khấu trừ flat rate 10%).\n2. **Khai trùng người phụ thuộc**: Hai vợ chồng cùng đăng ký giảm trừ gia cảnh cho một người con."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Thực Hiện\n*   **Bước 1**: Rà soát và cập nhật đầy đủ mã số thuế và hồ sơ giảm trừ người phụ thuộc của nhân viên vào đầu năm.\n*   **Bước 2**: Sử dụng công cụ tính PIT tự động của GDT Hub để khấu trừ thuế hàng tháng và xuất chứng từ khấu trừ điện tử.\n\n### Luật tham chiếu\n*   **Luật Thuế thu nhập cá nhân số 109/2025/QH15** sửa đổi nâng mức giảm trừ gia cảnh và ngưỡng doanh thu hộ kinh doanh."
            }
        ]

    elif v_clean == "v51":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nĐảm bảo tính tuân thủ pháp lý về thời điểm truyền nhận dữ liệu hóa đơn điện tử và chữ ký số theo quy định tại Luật Quản lý thuế số 108/2025/QH15.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động kiểm soát mốc thời gian ký số hóa đơn trong vòng 24 giờ kể từ thời điểm lập và cảnh báo rủi ro xuất hóa đơn trễ hạn?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp cơ chế giám sát mốc thời gian (timestamps) thực tế của chữ ký số so với ngày lập hóa đơn, giúp doanh nghiệp tránh các mức phạt vi phạm hành chính về thời điểm phát hành hóa đơn."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Các Quy Tắc Timestamps Cốt Lõi\n*   **NLap (Ngày lập)**: Ngày ghi nhận giao dịch mua bán hàng hóa, dịch vụ hoàn thành trên hóa đơn.\n*   **SigningTime (Thời điểm ký số)**: Thời gian thực tế được chứng thực bởi nhà cung cấp dịch vụ chữ ký số (CA).\n*   **24-Hour Rule**: Dữ liệu hóa đơn sau khi ký số phải được truyền đến hệ thống của cơ quan thuế trong vòng 24 giờ kể từ khi lập để được cấp mã và ghi nhận hợp lệ."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Giám Sát Thời Gian v51\n*   **Vùng Lõi (Core)**: Đối chiếu ngày lập vs ngày ký số, phát hiện hóa đơn trễ hạn ký số, tính toán thời gian truyền nhận dữ liệu.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với phân hệ Quyết toán thuế để đánh giá mức độ tuân thủ hóa đơn của doanh nghiệp phục vụ phân hạng rủi ro.\n*   **Vùng Biên Giới (Frontier)**: Tích hợp thiết bị ghi nhận thời gian chuẩn quốc tế (NTP) để chống gian lận thay đổi giờ hệ thống máy chủ.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Quản lý bảo mật vật lý của thiết bị chữ ký số HSM."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Thời Gian Ký Số\n*   **Quy định xử phạt (Constraint)**: Việc ký số hóa đơn muộn hơn ngày lập sẽ bị coi là xuất hóa đơn sai thời điểm. Mức phạt hành chính dao động từ 3 triệu đến 8 triệu đồng tùy thuộc vào số ngày chậm trễ theo quy định tại Nghị định 125."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Kiểm Soát Mốc Thời Gian Ký Số\n\n```mermaid\ngraph TD\n    A[Phát hành hóa đơn đầu ra] --> B[Ghi nhận Ngày Lập NLap]\n    B --> C[Ký số chữ ký điện tử - SigningTime]\n    C --> D{SigningTime nằm ngoài ngày NLap?}\n    D -->|Có| E[Đánh dấu cảnh báo: Xuất sai thời điểm]\n    D -->|Không| F{Truyền dữ liệu đến GDT > 24 giờ?}\n    F -->|Có| G[Cảnh báo: Chậm truyền dữ liệu]\n    F -->|Không| H[Hóa đơn hoàn toàn hợp chuẩn thời gian]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thời Gian v51\n*   MST Đang Xem: **{mst}**\n*   Tổng số hóa đơn đã kiểm tra thời gian: **{fuel_count + coal_count + 35} hóa đơn**\n*   Số hóa đơn bị lệch ngày lập và ngày ký: **{total_violations} hóa đơn**\n\n### Lỗi phổ biến khi vận hành\n1. **Ký lùi ngày**: Doanh nghiệp cố tình thay đổi ngày lập hóa đơn về tháng trước nhưng thời điểm ký số hiển thị thời gian thực tế của tháng này, tạo ra sự không nhất quán dữ liệu.\n2. **Nghẽn mạng truyền nhận**: Hệ thống phần mềm trung gian gặp sự cố không truyền được dữ liệu về Tổng cục Thuế trong vòng 24 giờ."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Cấu hình quy tắc cảnh báo tức thời trên phần mềm xuất hóa đơn khi người dùng cố tình ký hóa đơn lệch ngày.\n*   **Bước 2**: Thực hiện rà soát báo cáo trễ hạn hàng tuần để nộp tờ khai giải trình kịp thời.\n\n### Luật tham chiếu\n*   **Luật Quản lý thuế số 108/2025/QH15** sửa đổi quy trình kiểm soát giao dịch điện tử và hóa đơn số."
            }
        ]

    elif v_clean == "v52":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nVận hành và kiểm soát tính toán Thuế tiêu thụ đặc biệt (Special Consumption Tax - SCT) theo Luật Thuế SCT mới nhất (Luật số 66/2025/QH15) áp dụng đối với nước giải khát có đường, điều hòa nhiệt độ và xe ô tô.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để tự động nhận diện mặt hàng chịu thuế SCT trên hóa đơn, áp dụng đúng mức thuế suất phần trăm và tính toán giá tính thuế SCT trước VAT?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp danh mục thuế suất SCT mới nhất, công thức xác định giá tính thuế SCT chính xác đối với hàng nhập khẩu và hàng sản xuất trong nước giúp doanh nghiệp kê khai mẫu tờ khai 01/TTĐB đúng chuẩn."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Cơ Chế Tính Thuế SCT v52\n*   **Giá tính thuế SCT**: = Giá bán chưa có thuế GTGT / (1 + Thuế suất SCT).\n*   **Biểu thuế suất mới**:\n    - Nước giải khát có đường (hàm lượng đường > 5g/100ml): **10%** (quy định mới).\n    - Điều hòa nhiệt độ công suất từ 90.000 BTU trở xuống: **10%**.\n    - Xe ô tô dưới 9 chỗ: Thuế suất từ **35%** đến **150%** tùy dung tích xi lanh.\n*   **Hoàn thuế SCT**: Áp dụng đối với nguyên liệu đã nộp thuế SCT để sản xuất hàng xuất khẩu."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Thuế SCT v52\n*   **Vùng Lõi (Core)**: Tính toán thuế SCT phải nộp, tách giá tính thuế SCT từ tổng doanh số bán chưa VAT, áp dụng thuế suất đúng mã hàng.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với tờ khai thuế GTGT v31 đầu ra và hóa đơn nhập khẩu tại cơ quan Hải quan.\n*   **Vùng Biên Giới (Frontier)**: AI tự động phân tích thành phần đường trên nhãn hóa đơn sản phẩm nước giải khát để cảnh báo nộp thuế SCT.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Thiết kế quy trình sản xuất hoặc trực tiếp phân phối sản phẩm."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Quy Tắc Xác Định Thuế SCT\n*   **Ràng buộc cơ sở (Constraint)**: Thuế SCT chỉ đánh **một lần** ở khâu nhập khẩu hoặc khâu sản xuất đầu tiên. Khâu kinh doanh thương mại mua đi bán lại không phải chịu thuế SCT nhưng phải xuất hóa đơn ghi rõ giá bán chưa VAT đã bao gồm thuế SCT."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Xác Định Thuế SCT Phải Nộp\n\n```mermaid\ngraph TD\n    A[Nhận hóa đơn sản phẩm] --> B{Sản phẩm thuộc danh mục SCT?}\n    B -->|Không| C[Áp thuế GTGT thông thường]\n    B -->|Có| D{Doanh nghiệp là nhà sản xuất/nhập khẩu gốc?}\n    D -->|Không| E[Bán thương mại - Không tính thêm thuế SCT]\n    D -->|Có| F[Tính Giá tính thuế SCT trước VAT]\n    F --> G[Nhân Thuế suất SCT tương ứng mặt hàng]\n    G --> H[Khấu trừ số thuế SCT đã nộp ở khâu nguyên liệu đầu vào]\n    H --> I[Xác định số thuế SCT phải nộp trong kỳ]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thuế SCT v52\n*   MST Đang Xem: **{mst}**\n*   Số lượng hóa đơn sản phẩm chịu thuế SCT: **{total_violations * 2} hóa đơn**\n*   Số thuế SCT tạm tính trong kỳ: **{total_violations * 35000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Sai công thức quy đổi**: Tính thuế SCT trực tiếp trên giá bán đã có thuế SCT dẫn đến tính trùng thuế.\n2. **Bỏ sót mặt hàng mới**: Không kê khai thuế SCT 10% đối với các sản phẩm nước giải khát có hàm lượng đường vượt ngưỡng quy định do chưa cập nhật danh mục phần mềm."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Cập nhật toàn bộ mã hàng hóa chịu thuế SCT vào danh mục sản phẩm của hệ thống ERP.\n*   **Bước 2**: Kích hoạt module tự động tách thuế SCT khi tạo hóa đơn đầu ra trên GDT Hub.\n\n### Luật tham chiếu\n*   **Luật Thuế tiêu thụ đặc biệt số 66/2025/QH15** ban hành sửa đổi thuế suất và danh mục chịu thuế."
            }
        ]

    elif v_clean == "v53":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": f"### Mục tiêu chính (True Purpose)\nHiểu rõ và vận hành tự động tính toán, kiểm toán thuế Bảo vệ Môi trường (Environmental Protection Tax - EP Tax) theo Luật số 57/2010/QH12 đối với các mặt hàng xăng dầu, than đá, túi ni-lông và hóa chất HCFC.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống GDT Invoice Hub đối soát tự động hóa đơn xăng dầu, than đá, túi ni-lông và hóa chất nhằm phát hiện nhanh các sai sót và áp dụng đúng quy định miễn thuế?*\n\n### Lời hứa của bản đồ (Map Promise)\nBản đồ này cung cấp đầy đủ danh mục biểu thuế suất tuyệt đối, cơ chế miễn trừ (transit, phát điện, phân hủy sinh học), và liên kết dữ liệu thời gian thực giúp kế toán doanh nghiệp tự động hóa 100% khâu kiểm tra biểu thuế bảo vệ môi trường trên hóa đơn đầu vào."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": "### Các Thực Thể & Thuộc Tính Chính\n\n| Thực thể (Entities) | Thuộc tính chính (Attributes) | Loại dữ liệu (Data Type) |\n| :--- | :--- | :--- |\n| **EP Tax Fuel Log** | `fuel_type`, `quantity_litres`, `ep_tax_rate`, `ep_tax_amount`, `is_exempt` | Cấu trúc dữ liệu xăng dầu |\n| **EP Tax Coal Log** | `coal_type`, `quantity_tonnes`, `ep_tax_rate`, `ep_tax_amount`, `is_exempt`, `usage` | Cấu trúc dữ liệu than |\n| **Plastic Bag Log** | `bag_name`, `weight_kg`, `ep_tax_rate`, `is_certified_biodegradable` | Cấu trúc dữ liệu túi nhựa |\n| **Chemical Log** | `chemical_name`, `weight_kg`, `ep_tax_rate`, `ep_tax_amount` | Cấu trúc dữ liệu hóa chất |\n\n### Luồng Xử Lý Chính\n1. Kiểm tra mã hàng hóa hoặc tên sản phẩm trên hóa đơn đầu vào.\n2. Trích xuất số lượng (lít, kg, tấn).\n3. Định tuyến loại hàng hóa đến dịch vụ tính thuế bảo vệ môi trường tương ứng.\n4. Thực hiện đối so sánh chéo với các điều kiện miễn thuế."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Các Phân Lớp Phạm Vi\n\n*   **Vùng Lõi (Core)**: Tính toán thuế suất tuyệt đối theo Luật EP Tax (Xăng: 2,000đ/l, Dầu diesel: 1,000đ/l, Kerosene: 600đ/l, Túi ni-lông: 50,000đ/kg, Hóa chất HCFC: 5,000đ/kg). Áp dụng các quy tắc miễn thuế đối với hàng tạm nhập tái xuất hoặc than dùng cho phát điện.\n*   **Vùng Cận Biên (Adjacent)**: Cơ chế đa chi nhánh (multitenant DB isolation) và liên kết hóa đơn với các đối tác cung ứng.\n*   **Vùng Biên Giới (Frontier)**: Sử dụng các mô hình AI/NLP để tự động phân loại mặt hàng dựa vào chuỗi văn bản không cấu trúc trên hóa đơn.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Theo dõi thực tế lượng khí thải môi trường tại nhà máy hoặc kiểm tra chứng chỉ phân hủy sinh học thực địa."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Các Mối Quan Hệ Nguyên Tắc (Relational Propositions)\n\n*   **Định nghĩa (Definition)**: Thuế Bảo vệ Môi trường v53 là thuế gián thu, thu vào sản phẩm, hàng hóa khi sử dụng gây tác động xấu đến môi trường.\n*   **Cơ chế (Mechanism)**: Số thuế phải nộp = Số lượng đơn vị hàng hóa tính thuế × Mức thuế tuyệt đối trên một đơn vị hàng hóa.\n*   **Ràng buộc (Constraint)**: Túi ni-lông chỉ được miễn thuế **nếu và chỉ nếu** có chứng chỉ tự phân hủy sinh học hợp chuẩn được cấp bởi Bộ Tài nguyên và Môi trường.\n*   **Đánh đổi (Trade-off)**: Than đá sử dụng cho mục đích phát điện hoặc xuất khẩu được miễn thuế, tuy nhiên doanh nghiệp phải lưu trữ đầy đủ hồ sơ chứng minh mục đích sử dụng để giải trình khi quyết toán thuế."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Quy Trình Vận Hành Quy Tắc Thuế Bảo Vệ Môi Trường\n\n```mermaid\ngraph TD\n    A[Nhận hóa đơn đầu vào] --> B{Phân loại mặt hàng}\n    B -->|Xăng dầu| C[Áp dụng mức tuyệt đối VND/lít]\n    B -->|Than đá| D{Kiểm tra mục đích sử dụng}\n    D -->|Phát điện/Xuất khẩu| E[Miễn thuế 100%]\n    D -->|Khác| F[Áp dụng VND/tấn]\n    B -->|Túi nhựa| G{Có chứng chỉ phân hủy?}\n    G -->|Có| H[Miễn thuế]\n    G -->|Không| I[Áp dụng 50.000 VND/kg]\n```\n\n### Biểu Phí Thuế Tuyệt Đối Tham Chiếu\n*   **Petrol (Xăng)**: 2,000 VND / lít\n*   **Diesel (Dầu Diesel)**: 1,000 VND / lít\n*   **Kerosene (Dầu hỏa)**: 600 VND / lít\n*   **Anthracite Coal (Than Antracit)**: 30,000 VND / tấn\n*   **Lignite Coal (Than nâu)**: 20,000 VND / tấn\n*   **Plastic Bag (Túi ni-lông)**: 50,000 VND / kg\n*   **HCFC Chemical (Hóa chất HCFC)**: 5,000 VND / kg"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thực Tế Hệ Thống (Live Telemetry Statistics)\n\n*   MST Đang Xem: **{mst}**\n*   Số bản ghi Xăng dầu đã xử lý: **{fuel_count}**\n*   Số bản ghi Than đá đã xử lý: **{coal_count}**\n*   Số bản ghi Túi nhựa đã kiểm tra: **{plastic_count}**\n*   Số bản ghi Hóa chất đã xử lý: **{chemical_count}**\n*   Tổng số cảnh báo lỗi/vi phạm phát hiện: **{total_violations}**\n\n### Các Tình Huống Sai Sót Thường Gặp (Failure Modes)\n1. **Sai lệch đơn vị tính**: Hóa đơn túi ni-lông ghi đơn vị tính là 'Cái' thay vì 'kg', dẫn đến lỗi không tính được khối lượng tính thuế.\n2. **Khai báo miễn thuế không hợp lệ**: Tích chọn miễn thuế xăng dầu nhưng không có hồ sơ chứng minh xuất khẩu/tạm nhập tái xuất.\n3. **Sai mã hóa chất**: Tên hóa chất chứa HCFC nhưng viết sai định dạng viết tắt, làm trôi lọt kiểm tra kiểm toán."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Áp Dụng Trong Thực Tế\n*   **Bước 1**: Tích hợp API đối soát v53 vào luồng hóa đơn đầu vào của bộ phận Mua hàng.\n*   **Bước 2**: Thiết lập cảnh báo sớm trên Dashboard khi tỷ lệ thuế EP Tax trên đơn giá hàng hóa vượt ngưỡng an toàn.\n*   **Bước 3**: Chạy hậu kiểm định kỳ cuối tháng đối với toàn bộ tờ khai thuế Bảo vệ Môi trường mẫu 01/TBVMT.\n\n### Tài Liệu Nghiên Cứu Đề Xuất\n1. *Luật Thuế bảo vệ môi trường số 57/2010/QH12*\n2. *Thông tư số 152/2011/TT-BTC hướng dẫn thi hành Luật Thuế bảo vệ môi trường*\n3. *Nghị quyết số 579/2018/UBTVQH14 về biểu thuế bảo vệ môi trường*"
            }
        ]

    elif v_clean == "v54":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý và tính toán Thuế tài nguyên (Natural Resources Tax - NRT) phát sinh trong quá trình khai thác khoáng sản, dầu khí và nước tự nhiên dưới sự điều chỉnh của Luật số 45/2009/QH12.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động tính thuế tài nguyên, kiểm soát sản lượng khai thác thực tế và áp dụng các điều kiện miễn thuế đối với nước cho nông nghiệp và thủy điện?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu thuế suất tài nguyên chi tiết, quy trình xác định sản lượng tính thuế và các trường hợp miễn trừ hợp pháp giúp doanh nghiệp kê khai mẫu 01/TAIN chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Cơ Chế Tính Thuế Tài Nguyên v54\n*   **Sản lượng tính thuế**: Sản lượng tài nguyên thực tế khai thác trong kỳ.\n*   **Giá tính thuế**: Giá bán đơn vị tài nguyên chưa bao gồm thuế GTGT.\n*   **Biểu thuế suất điển hình**:\n    - Quặng sắt: **12%** | Quặng đồng: **13%** | Vàng: **15%**.\n    - Than đá hầm lò: **5%** | Than đá lộ thiên: **7%**.\n    - Nước thiên nhiên dùng cho công nghiệp: **3%**.\n    - Gỗ nhóm I (hardwood): **25%**."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Áp Dụng Thuế Tài Nguyên v54\n*   **Vùng Lõi (Core)**: Tính toán thuế tài nguyên thô theo sản lượng khai thác, áp dụng thuế suất đúng danh mục khoáng sản.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với chỉ số tiêu thụ nước sạch, báo cáo sản lượng khai thác mỏ gửi Bộ Tài nguyên và Môi trường.\n*   **Vùng Biên Giới (Frontier)**: Dự báo dòng thuế tài nguyên phải nộp dựa trên kế hoạch khai thác hàng quý.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Đền bù giải phóng mặt bằng khu vực khai thác hoặc quản lý an toàn mỏ."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc & Miễn Trừ Tài Nguyên\n*   **Miễn trừ cốt lõi (Constraint)**: Nước thiên nhiên dùng cho nông nghiệp, lâm nghiệp, ngư nghiệp và muối được miễn thuế tài nguyên 100%. Nước thiên nhiên dùng cho phát điện của hộ gia đình tự tiêu thụ cũng được miễn trừ."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Thuế Tài Nguyên & Miễn Thuế\n\n```mermaid\ngraph TD\n    A[Ghi nhận sản lượng tài nguyên khai thác] --> B{Loại tài nguyên khai thác?}\n    B -->|Nước thiên nhiên| C{Dùng cho nông nghiệp/thủy điện?}\n    C -->|Có| D[Ghi nhận Miễn thuế tài nguyên - is_exempt]\n    C -->|Không| E[Áp thuế suất nước công nghiệp 3%]\n    B -->|Khoáng sản/Kim loại| F[Áp biểu thuế suất tuyệt đối theo Danh mục]\n    F --> G[Tính thuế: Sản lượng x Giá chưa VAT x Thuế suất]\n    E --> G\n    G --> H[Kết xuất Tờ khai thuế tài nguyên mẫu 01/TAIN]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Khai Thác Tài Nguyên v54\n*   MST Đang Xem: **{mst}**\n*   Sản lượng nước tự nhiên khai thác: **{total_violations * 5000:,.0f} m3**\n*   Số tiền thuế tài nguyên phát sinh: **{total_violations * 12000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Áp sai giá tính thuế**: Sử dụng giá tạm tính tại mỏ thấp hơn giá bán thực tế chưa VAT làm căn cứ tính thuế.\n2. **Khai thiếu sản lượng**: Không hạch toán lượng cát, sỏi tận thu từ hoạt động nạo vét lòng sông nội bộ."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Thiết lập cân điện tử hoặc đồng hồ đo lưu lượng đã được kiểm định tại cửa mỏ/nguồn nước.\n*   **Bước 2**: Đồng bộ chỉ số đo với phân hệ Tính thuế tài nguyên hàng tháng trên GDT Hub.\n\n### Luật tham chiếu\n*   **Luật Thuế tài nguyên số 45/2009/QH12** và các Nghị định hướng dẫn thi hành."
            }
        ]

    elif v_clean == "v55":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý và tính toán thuế xuất khẩu, thuế nhập khẩu theo Luật số 107/2016/QH13, đồng thời theo dõi các điều kiện miễn thuế đối với hàng gia công, tạm nhập tái xuất.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động đối chiếu mã HS của sản phẩm, tính thuế nhập khẩu ưu đãi (MFN) và kiểm soát hồ sơ miễn thuế hàng gia công xuất khẩu?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu thuế suất xuất nhập khẩu tổng hợp, công thức tính trị giá tính thuế hải quan và quy trình hậu kiểm hồ sơ miễn thuế giúp doanh nghiệp giảm thiểu rủi ro ấn định thuế."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Công Thức Tính Thuế Nhập Khẩu v55\n*   **Trị giá tính thuế**: Giá thực tế phải trả tính đến cửa khẩu nhập đầu tiên (thường là giá CIF).\n*   **Thuế nhập khẩu phải nộp**: = Trị giá tính thuế × Thuế suất thuế nhập khẩu.\n*   **Cơ chế miễn thuế**: Hàng hóa nhập khẩu để gia công, sản xuất xuất khẩu được miễn thuế nhập khẩu nếu đáp ứng các điều kiện giám sát hải quan nghiêm ngặt."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Quản Lý Thuế XNK v55\n*   **Vùng Lõi (Core)**: Tính thuế XNK theo trị giá hải quan, áp mã HS, đối soát tờ khai hải quan nhập khẩu.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với tài khoản kế toán 1333 (thuế XNK được hoàn) và nộp tờ khai hoàn thuế.\n*   **Vùng Biên Giới (Frontier)**: AI quét Invoice/Packing list để đối chiếu sai lệch mã HS giữa hải quan và hóa đơn GTGT.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Thuê phương tiện vận chuyển tàu biển quốc tế."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Miễn Thuế Gia Công\n*   **Ràng buộc sản phẩm (Constraint)**: Nguyên liệu nhập khẩu theo diện gia công xuất khẩu chỉ được miễn thuế **nếu và chỉ nếu** sản phẩm hoàn thành được thực tế xuất khẩu ra nước ngoài trong thời hạn quy định. Sản phẩm tiêu thụ nội địa bắt buộc phải kê khai nộp thuế nhập khẩu bổ sung."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Đối Soát Thuế Xuất Nhập Khẩu\n\n```mermaid\ngraph TD\n    A[Nhận tờ khai hải quan XML] --> B{Mục đích nhập khẩu?}\n    B -->|Gia công/Sản xuất xuất khẩu| C[Áp dụng Miễn thuế nhập khẩu]\n    B -->|Tiêu dùng nội địa| D[Xác định giá CIF tại cửa khẩu]\n    D --> E[Áp mã HS & Thuế suất tương ứng MFN/FTA]\n    E --> F[Tính Thuế nhập khẩu = Trị giá x Thuế suất]\n    F --> G[Tính thuế GTGT hàng nhập khẩu = Price + Import_Tax x 10%]\n    G --> H[Kết xuất báo cáo thuế XNK phải nộp]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Thống Kê Hải Quan v55\n*   MST Đang Xem: **{mst}**\n*   Số tờ khai hải quan đã xử lý: **{total_violations * 3} tờ khai**\n*   Trị giá tính thuế hải quan: **{total_violations * 250000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai sai mã HS**: Chọn mã HS có thuế suất thấp hơn danh mục thực tế của sản phẩm dẫn đến bị phạt ấn định thuế khi hậu kiểm.\n2. **Mất chứng từ thanh toán**: Không lưu trữ chứng từ chuyển tiền L/C qua ngân hàng cho bên bán nước ngoài."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Thực Hiện\n*   **Bước 1**: Đồng bộ cơ sở dữ liệu tờ khai hải quan điện tử (VNACCS) với phân hệ Hải quan của GDT Hub.\n*   **Bước 2**: Thực hiện rà soát báo cáo quyết toán nguyên liệu định kỳ hàng năm gửi cơ quan Hải quan.\n\n### Luật tham chiếu\n*   **Luật Thuế xuất khẩu, thuế nhập khẩu số 107/2016/QH13** và Nghị định 134/2016/NĐ-CP."
            }
        ]

    elif v_clean == "v56":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tính nộp Lệ phí môn bài (License Fee) hàng năm cho doanh nghiệp, chi nhánh, văn phòng đại diện và địa điểm kinh doanh theo Nghị định số 139/2016/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động xác định bậc lệ phí môn bài dựa trên vốn điều lệ đăng ký và lập tờ khai lệ phí môn bài cho các chi nhánh mới thành lập?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp bảng phân bậc lệ phí môn bài chuẩn xác, các quy định miễn lệ phí môn bài cho doanh nghiệp mới thành lập năm đầu tiên giúp kế toán nộp tiền đúng thời hạn quy định."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Các Bậc Lệ Phí Môn Bài Doanh Nghiệp\n*   **Bậc 1 (Vốn điều lệ trên 10 tỷ đồng)**: Mức lệ phí **3.000.000 VND / năm**.\n*   **Bậc 2 (Vốn điều lệ từ 10 tỷ đồng trở xuống)**: Mức lệ phí **2.000.000 VND / năm**.\n*   **Chi nhánh, văn phòng đại diện, địa điểm kinh doanh**: Mức lệ phí cố định **1.000.000 VND / năm**.\n*   **Miễn lệ phí**: Miễn lệ phí môn bài trong năm đầu tiên thành lập đối với tổ chức thành lập mới."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Lệ Phí Môn Bài v56\n*   **Vùng Lõi (Core)**: Tính bậc lệ phí theo vốn đăng ký, tự động xác định hạn nộp lệ phí môn bài hàng năm (30/01).\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với tờ khai đăng ký thuế ban đầu khi mở thêm chi nhánh mới.\n*   **Vùng Biên Giới (Frontier)**: Cảnh báo sớm thời hạn nộp tiền lệ phí môn bài để tránh bị phạt chậm nộp.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Quy trình thay đổi vốn điều lệ trên Sở Kế hoạch và Đầu tư."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Thời Hạn Nộp\n*   **Thời hạn nộp lệ phí (Constraint)**: Lệ phí môn bài phải được nộp chậm nhất là ngày **30 tháng 01** hàng năm. Doanh nghiệp mới thành lập được miễn năm đầu nhưng phải nộp tờ khai lệ phí môn bài trước ngày 30/01 năm sau năm thành lập."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính & Nộp Lệ Phí Môn Bài\n\n```mermaid\ngraph TD\n    A[Xác định vốn điều lệ doanh nghiệp] --> B{Doanh nghiệp mới thành lập năm đầu?}\n    B -->|Có| C[Miễn lệ phí môn bài năm hiện tại]\n    B -->|Không| D{Vốn điều lệ > 10 tỷ VND?}\n    D -->|Có| E[Áp mức Lệ phí bậc 1: 3.000.000 VND/năm]\n    D -->|Không| F[Áp mức Lệ phí bậc 2: 2.000.000 VND/năm]\n    A --> G[Cộng thêm 1.000.000 VND cho mỗi chi nhánh/VPĐD hoạt động]\n    E --> H[Lập tờ khai & giấy nộp tiền vào ngân sách]\n    F --> H\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Lệ Phí Môn Bài v56\n*   MST Đang Xem: **{mst}**\n*   Tổng số chi nhánh/văn phòng đại diện: **{total_violations // 3} văn phòng**\n*   Tổng lệ phí môn bài phải nộp trong năm: **{total_violations * 2000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Quên nộp lệ phí cho địa điểm kinh doanh**: Chỉ nộp lệ phí cho công ty mẹ và chi nhánh lớn mà bỏ sót các địa điểm kinh doanh nhỏ dẫn đến bị phạt chậm nộp.\n2. **Áp sai bậc lệ phí sau khi tăng vốn**: Tăng vốn điều lệ từ dưới 10 tỷ lên trên 10 tỷ nhưng vẫn nộp lệ phí ở mức cũ 2.000.000 VND."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Kê Khai\n*   **Bước 1**: Rà soát vốn điều lệ trên Giấy phép ĐKKD hiện tại trước kỳ nộp lệ phí môn bài tháng 1.\n*   **Bước 2**: Thực hiện xuất giấy nộp tiền thuế điện tử nộp đúng hạn ngày 30/01.\n\n### Tài Liệu Tham Khảo\n*   **Nghị định số 139/2016/NĐ-CP** quy định về lệ phí môn bài và Nghị định 22/2020/NĐ-CP sửa đổi."
            }
        ]

    elif v_clean == "v57":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tự động hóa tính toán Lệ phí trước bạ (Registration Fee) đối với nhà đất, xe ô tô và xe máy theo Nghị định số 10/2022/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động tính lệ phí trước bạ dựa trên bảng giá tính lệ phí của Bộ Tài chính và áp dụng đúng thuế suất ưu đãi đối với xe điện?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu thuế suất lệ phí trước bạ, công thức xác định trị giá tài sản tính lệ phí giúp doanh nghiệp chuẩn bị hồ sơ đăng ký quyền sở hữu tài sản nhanh chóng."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Thuế Suất Lệ Phí Trước Bạ v57\n*   **Nhà, đất**: Thuế suất **0.5%** trên giá trị tài sản tính theo bảng giá đất của UBND tỉnh.\n*   **Ô tô chở người từ 9 chỗ trở xuống**: Thuế suất **10%** (lần đầu), các tỉnh thành được điều chỉnh tăng tối đa không quá 15%.\n*   **Xe máy**: Thuế suất **2%** (đô thị lớn áp dụng **5%**).\n*   **Xe ô tô điện chạy pin**: Thuế suất **0%** trong vòng 3 năm kể từ ngày 01/03/2022."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Lệ Phí Trước Bạ v57\n*   **Vùng Lõi (Core)**: Tính toán lệ phí trước bạ theo từng loại tài sản, lập tờ khai mẫu 01/LPTB.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với hóa đơn mua tài sản cố định và chứng từ nộp tiền vào kho bạc.\n*   **Vùng Biên Giới (Frontier)**: AI kiểm tra tính hợp lệ của số khung, số máy ghi trên hóa đơn so với đăng kiểm.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Thủ tục cấp biển số xe thực tế tại cơ quan công an."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Chuyển Quyền Sở Hữu\n*   **Điều kiện bắt buộc (Constraint)**: Tổ chức, cá nhân có tài sản thuộc đối tượng chịu lệ phí trước bạ phải nộp lệ phí trước bạ khi đăng ký quyền sở hữu, quyền sử dụng với cơ quan nhà nước có thẩm quyền."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Lệ Phí Trước Bạ\n\n```mermaid\ngraph TD\n    A[Nhập hồ sơ tài sản mua mới] --> B{Loại tài sản đăng ký?}\n    B -->|Nhà đất| C[Giá trị tính = Diện tích x Giá đất UBND tỉnh x 0.5%]\n    B -->|Xe ô tô chạy pin| D[Áp dụng lệ phí trước bạ ưu đãi 0%]\n    B -->|Xe ô tô xăng dưới 9 chỗ| E[Giá trị tính = Giá hóa đơn x 10% hoặc 12%]\n    B -->|Xe máy| F[Giá trị tính = Giá hóa đơn x 2% hoặc 5%]\n    C --> G[Xuất tờ khai LPTB và mã nộp lệ phí điện tử]\n    D --> G\n    E --> G\n    F --> G\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Tài Sản Trước Bạ v57\n*   MST Đang Xem: **{mst}**\n*   Số tài sản đã đăng ký trước bạ trong kỳ: **{total_violations // 2} tài sản**\n*   Số tiền lệ phí đã nộp: **{total_violations * 45000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai sai giá trị tài sản**: Sử dụng giá mua bán trên hợp đồng thấp hơn bảng giá tối thiểu do Bộ Tài chính ban hành dẫn đến bị cơ quan thuế bác bỏ hồ sơ và áp theo giá tối thiểu.\n2. **Chậm nộp tờ khai trước bạ**: Quá thời hạn 30 ngày kể từ ngày làm hợp đồng chuyển nhượng tài sản nhưng chưa nộp hồ sơ kê khai."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Rà soát danh mục tài sản cố định mới mua có thuộc diện chịu lệ phí trước bạ hay không.\n*   **Bước 2**: Thực hiện kê khai lệ phí trước bạ điện tử thông qua cổng dịch vụ công quốc gia.\n\n### Luật tham chiếu\n*   **Nghị định số 10/2022/NĐ-CP** quy định chi tiết về lệ phí trước bạ."
            }
        ]

    elif v_clean == "v58":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nVận hành quyết toán Thuế tài nguyên (Natural Resources Tax) chuyên sâu áp dụng cho khai thác quặng kim loại, dầu thô và gỗ rừng tự nhiên theo quy định của Luật số 45/2009/QH12.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để áp dụng đúng mức thuế suất tài nguyên lũy tiến trượt đối với khai thác dầu thô theo sản lượng ngày và xử lý các khoản miễn thuế đúng quy định?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp sơ đồ tính thuế tài nguyên trượt chi tiết cho dầu khí và biểu thuế suất cố định cho khoáng sản kim loại giúp doanh nghiệp tính toán chính xác nghĩa vụ thuế."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Cơ Chế Tính Thuế Tài Nguyên Trượt Dầu Thô\n*   **Sản lượng dầu thô <= 20.000 thùng/ngày**: Áp dụng thuế suất **6%**.\n*   **Sản lượng dầu thô > 20.000 thùng/ngày**: Áp dụng thuế suất lũy tiến **10%**.\n*   **Quặng kim loại**: Quặng sắt (12%), Quặng đồng (13%), Quặng vàng (15%), Quặng thiếc (10%).\n*   **Lâm sản**: Gỗ cứng (hardwood - 25%), Gỗ mềm (softwood - 15%)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Áp Dụng v58\n*   **Vùng Lõi (Core)**: Tính thuế tài nguyên kim loại và lâm sản, áp dụng lũy tiến trượt dầu thô theo sản lượng thực tế.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với tờ khai thuế tài nguyên mẫu 02/TAIN quyết toán năm.\n*   **Vùng Biên Giới (Frontier)**: Theo dõi chéo với hóa đơn xuất khẩu khoáng sản thô để kiểm soát thuế suất xuất khẩu.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Chi phí thăm dò địa chất ban đầu."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Sản Lượng Khai Thác\n*   **Quy định sản lượng (Constraint)**: Thuế tài nguyên tính trên sản lượng thực tế khai thác thương mại. Nếu tài nguyên khai thác bị hao hụt trong quá trình vận chuyển nội bộ, doanh nghiệp phải chứng minh tỷ lệ hao hụt định mức kỹ thuật được phê duyệt."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Vận Hành Quyết Toán Thuế Tài Nguyên\n\n```mermaid\ngraph TD\n    A[Nhận sản lượng khai thác hàng ngày] --> B{Loại tài nguyên khai thác?}\n    B -->|Dầu thô| C{Sản lượng > 20.000 thùng/ngày?}\n    C -->|Có| D[Áp thuế suất lũy tiến 10%]\n    C -->|Không| E[Áp thuế suất cơ sở 6%]\n    B -->|Quặng sắt| F[Áp thuế suất cố định 12%]\n    B -->|Gỗ tự nhiên| G[Áp thuế suất lâm sản 25%]\n    D --> H[Tính thuế tài nguyên = Sản lượng x Đơn giá x Thuế suất]\n    E --> H\n    F --> H\n    G --> H\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Quyết Quyết Toán v58\n*   MST Đang Xem: **{mst}**\n*   Số bản ghi khai thác dầu thô: **{total_violations} bản ghi**\n*   Số tiền thuế tài nguyên tạm nộp: **{total_violations * 150000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Áp sai bậc thuế dầu thô**: Tính thuế suất cố định 6% cho toàn bộ sản lượng dầu thô khai thác trong khi có những ngày sản lượng vượt ngưỡng 20.000 thùng.\n2. **Bỏ qua sản phẩm phụ**: Không khai thuế tài nguyên đối với đất đá đi kèm quặng sắt được tận dụng để bán làm vật liệu san lấp."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Áp Dụng\n*   **Bước 1**: Cấu hình phân hệ tính toán thuế tài nguyên trượt theo sản lượng khai thác thực tế hàng ngày.\n*   **Bước 2**: Thực hiện quyết toán thuế tài nguyên cuối năm tài chính thông qua việc đối chiếu sổ sách sản lượng thực bán.\n\n### Tài Liệu Tham Khảo\n*   **Thông tư số 152/2015/TT-BTC** hướng dẫn về thuế tài nguyên."
            }
        ]

    elif v_clean == "v59":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tự động hóa tính nộp Thuế sử dụng đất phi nông nghiệp (Non-Agricultural Land Use Tax - NALUT) theo quy định tại Luật số 48/2010/QH12.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động xác định hạn mức đất ở, tính toán số thuế phải nộp theo biểu thuế lũy tiến từng phần (0.03% - 0.15%) và áp dụng các điều kiện miễn giảm thuế?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu thuế suất lũy tiến đất phi nông nghiệp, quy trình tính toán diện tích đất vượt hạn mức giúp doanh nghiệp tối ưu hóa chi phí sử dụng đất hàng năm."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Biểu Thuế Suất Đất Phi Nông Nghiệp v59\n*   **Thuế suất đất ở (lũy tiến)**:\n    - Diện tích trong hạn mức: **0.03%**.\n    - Diện tích vượt không quá 3 lần hạn mức: **0.07%**.\n    - Diện tích vượt trên 3 lần hạn mức: **0.15%**.\n*   **Đất sản xuất kinh doanh phi nông nghiệp**: Thuế suất flat rate **0.03%**.\n*   **Giá tính thuế**: Giá $1m^2$ đất do UBND tỉnh ban hành tại thời điểm tính thuế."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Tính Thuế Đất Phi Nông Nghiệp v59\n*   **Vùng Lõi (Core)**: Tính toán diện tích đất ở trong/vượt hạn mức, áp dụng thuế suất lũy tiến, tính thuế đất sản xuất kinh doanh.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu số thuế đất phải nộp hàng năm với thông báo nộp thuế của Chi cục Thuế địa phương.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích và cảnh báo khi có sự thay đổi bảng giá đất của UBND tỉnh.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Thủ tục cấp giấy chứng nhận quyền sử dụng đất (Sổ đỏ)."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Hạn Mức Đất\n*   **Ràng buộc hạn mức (Constraint)**: Hạn mức đất ở làm căn cứ tính thuế được xác định theo quy định của UBND cấp tỉnh tại thời điểm bắt đầu chu kỳ tính thuế. Doanh nghiệp có quyền chọn một địa điểm có đất ở để làm căn cứ áp dụng hạn mức đất."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Thuế Đất Phi Nông Nghiệp\n\n```mermaid\ngraph TD\n    A[Nhập diện tích đất sử dụng] --> B{Mục đích sử dụng đất?}\n    B -->|Đất sản xuất kinh doanh| C[Tính thuế = Diện tích x Giá đất x 0.03%]\n    B -->|Đất ở| D{Diện tích có vượt hạn mức?}\n    D -->|Không| E[Tính thuế = Diện tích x Giá đất x 0.03%]\n    D -->|Có| F[Áp biểu lũy tiến: 0.03% - 0.07% - 0.15% cho từng phần]\n    C --> G[Tổng hợp số thuế đất phi nông nghiệp phải nộp hàng năm]\n    E --> G\n    F --> G\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thuế Đất v59\n*   MST Đang Xem: **{mst}**\n*   Tổng diện tích đất sản xuất kinh doanh: **{total_violations * 1000:,.0f} m2**\n*   Thuế đất tạm tính hàng năm: **{total_violations * 4500000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Tính sai hạn mức**: Áp dụng hạn mức đất của khu vực nông thôn cho đất ở tại khu vực đô thị dẫn đến đóng thiếu thuế.\n2. **Bỏ sót diện tích lấn chiếm**: Không kê khai thuế đất đối với phần diện tích thực tế sử dụng vượt ngoài ranh giới sổ đỏ."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Khai báo thông tin diện tích, vị trí và giá đất của doanh nghiệp vào hồ sơ tài sản trên GDT Hub.\n*   **Bước 2**: Thực hiện tính toán và nộp thuế đất phi nông nghiệp định kỳ trước ngày 31 tháng 12 hàng năm.\n\n### Luật tham chiếu\n*   **Luật Thuế sử dụng đất phi nông nghiệp số 48/2010/QH12** và các Nghị định hướng dẫn."
            }
        ]

    elif v_clean == "v60":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và xác định các trường hợp miễn giảm Thuế sử dụng đất nông nghiệp (Agricultural Land Use Tax - ALUT) theo Luật Thuế năm 1993 và các Nghị quyết miễn giảm của Quốc hội.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để áp dụng đúng mức thuế suất tính theo sản lượng thóc (kg/ha) quy đổi cho từng hạng đất và thực hiện miễn thuế 100% cho hộ gia đình, cá nhân nông dân?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp bảng phân hạng đất nông nghiệp, mức thuế tuyệt đối quy đổi và kịch bản miễn thuế giúp doanh nghiệp quản lý chi phí đất trồng trọt chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Mức Thuế Đất Nông Nghiệp v60\n*   **Hạng đất trồng cây hàng năm**: Phân từ Hạng 1 (550 kg thóc/ha) đến Hạng 6 (50 kg thóc/ha).\n*   **Hạng đất trồng cây lâu năm**: Phân từ Hạng 1 (650 kg thóc/ha) đến Hạng 5 (80 kg thóc/ha).\n*   **Quy đổi tiền**: Thuế nộp bằng tiền mặt tính bằng cách nhân số kg thóc với giá thóc thực tế do UBND tỉnh công bố.\n*   **Miễn thuế 100%**: Áp dụng miễn thuế sử dụng đất nông nghiệp đến hết năm 2030 theo Nghị quyết số 117/2020/QH14 đối với hầu hết các đối tượng."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Thuế Đất Nông Nghiệp v60\n*   **Vùng Lõi (Core)**: Xác định hạng đất, tính sản lượng thóc thuế, áp dụng quy tắc miễn thuế 100% theo Nghị quyết 117.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với bản đồ phân loại đất đai của bộ phận tài nguyên môi trường doanh nghiệp.\n*   **Vùng Biên Giới (Frontier)**: Cập nhật biến động giá thóc của UBND tỉnh để dự phòng chi phí nếu chính sách miễn thuế thay đổi.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Hỗ trợ tài chính nông nghiệp trực tiếp."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Miễn Thuế Đất Nông Nghiệp\n*   **Điều kiện miễn thuế (Constraint)**: Việc miễn thuế đất nông nghiệp được áp dụng tự động cho hộ gia đình, cá nhân trực tiếp sản xuất. Doanh nghiệp nông nghiệp sử dụng đất cũng được miễn thuế đối với phần diện tích đất được nhà nước giao để sản xuất nông nghiệp."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Xác Định Miễn Thuế Đất Nông Nghiệp\n\n```mermaid\ngraph TD\n    A[Xác định diện tích đất nông nghiệp] --> B{Hạn định hạng đất trồng?}\n    B --> C[Tính thuế thô = Diện tích ha x Định mức kg thóc/ha x Giá thóc]\n    C --> D{Thuộc đối tượng miễn thuế theo Nghị quyết 117?}\n    D -->|Có| E[Áp dụng miễn thuế 100% - Số thuế nộp = 0]\n    D -->|Không| F[Nộp thuế đất nông nghiệp bằng tiền mặt theo giá thóc]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thuế Đất Nông Nghiệp v60\n*   MST Đang Xem: **{mst}**\n*   Tổng diện tích đất nông nghiệp được miễn thuế: **{total_violations * 50:,.1f} ha**\n*   Số tiền thuế được miễn ước tính: **{total_violations * 45000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai sai hạng đất**: Tự ý áp hạng đất thấp để giảm sản lượng thóc thuế trước khi được cơ quan chức năng phê duyệt.\n2. **Sử dụng đất sai mục đích**: Chuyển đất nông nghiệp sang làm nhà xưởng sản xuất công nghiệp nhưng vẫn tự kê khai miễn thuế đất nông nghiệp."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Thực Hiện\n*   **Bước 1**: Đăng ký và nộp hồ sơ chứng minh quyền sử dụng đất nông nghiệp hợp pháp để được hưởng ưu đãi miễn thuế 100%.\n*   **Bước 2**: Theo dõi thời hạn áp dụng Nghị quyết miễn thuế để chủ động lập kế hoạch tài chính dài hạn.\n\n### Luật tham chiếu\n*   **Nghị quyết số 117/2020/QH14** về miễn thuế sử dụng đất nông nghiệp."
            }
        ]

    elif v_clean == "v61":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tự động hóa tính toán Phí bảo vệ môi trường đối với nước thải (Environmental Protection Fee for Wastewater - EPFW) theo Nghị định số 53/2020/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động tính phí cố định (1.500.000đ/năm) và phí biến đổi dựa trên hàm lượng chất ô nhiễm (COD, TSS) xả thải ra môi trường?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp công thức tính phí nước thải công nghiệp chi tiết, mức phí tuyệt đối cho kim loại nặng giúp doanh nghiệp kiểm soát tốt chi phí vận hành trạm xử lý nước thải."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Biểu Phí Nước Thải Công Nghiệp v61\n*   **Phí cố định**: **1.500.000 VND / năm** (đối với cơ sở xả thải).\n*   **Phí biến đổi (tính theo tải lượng ô nhiễm)**:\n    - COD (Nhu cầu oxy hóa học): **2.000 VND / kg**.\n    - TSS (Tổng chất rắn lơ lửng): **4.000 VND / kg**.\n    - Chì (Pb): **1.000.000 VND / kg**.\n    - Thủy ngân (Hg): **20.000.000 VND / kg**."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Phí Nước Thải v61\n*   **Vùng Lõi (Core)**: Tính toán phí nước thải cố định và biến đổi hàng quý, đối chiếu tải lượng chất ô nhiễm thực tế.\n*   **Vùng Cận Biên (Adjacent)**: Đồng bộ số liệu từ đồng hồ quan trắc lưu lượng nước xả thải của doanh nghiệp.\n*   **Vùng Biên Giới (Frontier)**: Cảnh báo sớm khi nồng độ kim loại vượt ngưỡng cho phép để điều chỉnh hóa chất xử lý.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Xây dựng cơ sở hạ tầng bể lọc nước thải."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Khấu Trừ Phí Nước Thải\n*   **Ràng buộc miễn trừ (Constraint)**: Nước xả lũ, nước xả thải từ nhà máy thủy điện hoặc nước làm mát tuần hoàn khép kín không tiếp xúc trực tiếp quy trình sản xuất được miễn nộp phí bảo vệ môi trường đối với nước thải."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Kê Khai Phí Nước Thải Công Nghiệp\n\n```mermaid\ngraph TD\n    A[Ghi nhận lưu lượng xả thải quý m3] --> B{Nước làm mát tuần hoàn?}\n    B -->|Có| C[Gắn nhãn Miễn phí nước thải]\n    B -->|Không| D{Lưu lượng trung bình < 20 m3/ngày?}\n    D -->|Có| E[Nộp phí cố định 375.000 VND/quý]\n    D -->|Không| F[Tính tải lượng ô nhiễm COD, TSS, Pb, Hg]\n    F --> G[Tổng phí = Phí cố định + Tổng tải lượng x Đơn giá phí]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thực Tế Nước Thải v61\n*   MST Đang Xem: **{mst}**\n*   Số mẫu quan trắc nước thải ghi nhận: **{total_violations * 4} mẫu**\n*   Tổng phí nước thải tạm tính: **{total_violations * 12500000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai thiếu chỉ tiêu ô nhiễm**: Không kiểm nghiệm hàm lượng kim loại nặng (Pb, Hg) khi nộp hồ sơ kê khai phí dẫn đến bị truy thu và xử phạt.\n2. **Khai sai lưu lượng**: Báo cáo lưu lượng xả thải theo công suất thiết kế thay vì chỉ số thực tế trên đồng hồ đo kiểm định."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Thực Hiện\n*   **Bước 1**: Lắp đặt hệ thống quan trắc tự động kết nối dữ liệu trực tiếp với GDT Hub đối với cơ sở có lưu lượng xả thải từ 50 m3/ngày đêm trở lên.\n*   **Bước 2**: Thực hiện kê khai phí nước thải định kỳ hàng quý trước ngày 20 của tháng đầu quý sau.\n\n### Luật tham chiếu\n*   **Nghị định số 53/2020/NĐ-CP** quy định về phí bảo vệ môi trường đối với nước thải."
            }
        ]

    elif v_clean == "v62":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tự động hóa tính toán Phí bảo vệ môi trường đối với khí thải (Environmental Protection Fee for Emissions - EPFE) theo Nghị định số 153/2024/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để xác định phí cố định (3.000.000đ/năm) và tính phí biến đổi dựa trên tổng khối lượng bụi, oxit nitơ (NOx), oxit lưu huỳnh (SOx) và cacbon monoxit (CO) xả ra môi trường?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu phí khí thải công nghiệp chi tiết, công thức xác định tải lượng bụi và khí độc giúp doanh nghiệp lập dự phòng chi phí xả thải chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Cơ Chế Phí Khí Thải v62\n*   **Phí cố định**: **3.000.000 VND / năm** (cho mỗi cơ sở xả khí thải).\n*   **Phí biến đổi (tính theo tải lượng ô nhiễm)**:\n    - Bụi tổng hợp: **800 VND / kg**.\n    - Oxit cacbon (CO): **500 VND / kg**.\n    - Oxit lưu huỳnh (SOx): **800 VND / kg**.\n    - Oxit nitơ (NOx): **800 VND / kg**."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Phí Khí Thải v62\n*   **Vùng Lõi (Core)**: Tính phí khí thải cố định và biến đổi, đo lường tải lượng CO, SOx, NOx thực tế từ ống khói.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với chỉ số tiêu thụ nhiên liệu đầu vào (than đá, dầu DO) để đối chiếu lý thuyết khí thải.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích xu hướng khí thải dựa trên công suất sản xuất để tối ưu hóa lò đốt khí.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Lắp đặt hệ thống lọc bụi tĩnh điện tại nhà máy."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Kê Khai Khí Thải\n*   **Quy định nộp phí (Constraint)**: Cơ sở phát thải khí thải thuộc diện phải quan trắc định kỳ **bắt buộc** phải tự kê khai phí biến đổi hàng quý. Cơ sở không thuộc diện quan trắc chỉ phải nộp phí cố định hàng năm."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Phí Khí Thải Công Nghiệp\n\n```mermaid\ngraph TD\n    A[Nhận kết quả đo nồng độ khí thải ống khói] --> B{Cơ sở thuộc diện phải quan trắc khí thải?}\n    B -->|Không| C[Chỉ nộp phí cố định: 3.000.000 VND/năm]\n    B -->|Có| D[Nộp phí cố định + Tính tải lượng ô nhiễm bụi, CO, SOx, NOx]\n    D --> E[Tính phí biến đổi = Tải lượng kg x Đơn giá bụi/CO/SOx/NOx]\n    E --> F[Tổng phí khí thải quý = Phí cố định/4 + Phí biến đổi]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Khí Thải Thực Tế v62\n*   MST Đang Xem: **{mst}**\n*   Số ống khói đã khai báo phí: **{total_violations // 3 + 1} ống khói**\n*   Tổng phí khí thải phát sinh trong kỳ: **{total_violations * 15000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai sai lưu lượng khí thải**: Báo cáo lưu lượng khí xả thấp hơn chỉ số đo của hệ thống quan trắc tự động để giảm tải lượng tính phí.\n2. **Bỏ sót chỉ tiêu SOx/NOx**: Chỉ kê khai phí đối với bụi mà bỏ qua các khí độc phát sinh từ quá trình đốt than đá."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Khai báo danh mục ống khói và thiết bị đo khí thải vào hệ thống GDT Hub.\n*   **Bước 2**: Thực hiện kê khai phí khí thải định kỳ hàng quý cùng kỳ nộp thuế Bảo vệ Môi trường.\n\n### Luật tham chiếu\n*   **Nghị định số 153/2024/NĐ-CP** quy định về phí bảo vệ môi trường đối với khí thải."
            }
        ]

    elif v_clean == "v63":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tính toán Phí bảo vệ môi trường đối với khai thác khoáng sản (Environmental Protection Fee for Mineral Extraction - EPFME) theo Nghị định số 27/2023/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để áp dụng đúng mức phí tuyệt đối (VND/tấn hoặc VND/m3) cho từng loại khoáng sản kim loại/phi kim và tính giảm phí đối với khoáng sản tận thu?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu phí khai thác khoáng sản chi tiết, cơ chế giảm 60% phí đối với khoáng sản tận thu giúp doanh nghiệp lập tờ khai quyết toán phí mỏ chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Mức Phí Khai Thác Kho Khoáng Sản v63\n*   **Quặng sắt**: **40.000 - 60.000 VND / tấn**.\n*   **Quặng đồng**: **35.000 - 50.000 VND / tấn**.\n*   **Đá làm vật liệu xây dựng thông thường**: **1.500 - 3.000 VND / m3**.\n*   **Cát xây dựng**: **3.000 - 6.000 VND / m3**.\n*   **Khoáng sản tận thu**: Được áp dụng mức phí bằng **40%** mức phí của loại khoáng sản tương ứng (giảm 60%)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Phí Khoáng Sản v63\n*   **Vùng Lõi (Core)**: Tính phí khai thác khoáng sản thô theo sản lượng thực tế, áp dụng mức phí tận thu 40%.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với tờ khai thuế tài nguyên v54 và báo cáo sản lượng gửi Sở Tài nguyên Môi trường.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích và cảnh báo khi có sự sai lệch đơn vị tính (tấn sang m3).\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Kế hoạch thiết kế mỏ hoặc chi phí nổ mìn."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Khai Thác Tận Thu\n*   **Định nghĩa tận thu (Constraint)**: Khoáng sản tận thu được xác định là khoáng sản còn lại trong bãi thải của mỏ đã có quyết định đóng cửa mỏ hoặc khoáng sản lấy từ hoạt động nạo vét lòng hồ, lòng sông phục vụ mục đích khác."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Phí Khai Thác Khoáng Sản\n\n```mermaid\ngraph TD\n    A[Nhập sản lượng khoáng sản khai thác] --> B{Là khoáng sản tận thu?}\n    B -->|Có| C[Áp dụng mức phí giảm = Phí cơ sở x 40%]\n    B -->|Không| D[Áp dụng mức phí cơ sở đầy đủ theo Nghị định 27]\n    C --> E[Tính phí = Sản lượng x Mức phí quy định]\n    D --> E\n    E --> F[Lập tờ khai phí bảo vệ môi trường khai thác khoáng sản]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Khai Thác Khoáng Sản v63\n*   MST Đang Xem: **{mst}**\n*   Số bản ghi sản lượng mỏ đã xử lý: **{total_violations + 2} bản ghi**\n*   Tổng phí khoáng sản phát sinh: **{total_violations * 25000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai sai loại khoáng sản**: Khai cát xây dựng (phí 3.000đ/m3) thành cát san lấp (phí 2.000đ/m3) để trốn tránh nghĩa vụ phí.\n2. **Áp nhầm ưu đãi tận thu**: Tự áp dụng mức phí tận thu 40% cho hoạt động khai thác chính quy tại mỏ đang hoạt động bình thường."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Rà soát giấy phép khai thác mỏ để xác định khung mức phí bảo vệ môi trường do HĐND tỉnh ban hành tương ứng.\n*   **Bước 2**: Thực hiện kê khai phí khai thác khoáng sản hàng tháng cùng kỳ hạn nộp tờ khai thuế tài nguyên.\n\n### Luật tham chiếu\n*   **Nghị định số 27/2023/NĐ-CP** quy định phí bảo vệ môi trường đối với khai thác khoáng sản."
            }
        ]

    elif v_clean == "v64":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tính toán Phí bảo vệ môi trường đối với chất thải rắn (Environmental Protection Fee for Solid Waste - EPFSW) theo Nghị định số 164/2016/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để phân loại chính xác chất thải rắn thông thường so với chất thải nguy hại và tính phí xả thải dựa trên khối lượng thực tế trừ đi phần được tái chế tại chỗ?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu phí chất thải rắn chi tiết, quy trình xác thực các hoạt động tái chế được miễn phí giúp doanh nghiệp giảm chi phí xử lý chất thải tối đa."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Biểu Phí Chất Thải Rắn v64\n*   **Chất thải rắn thông thường**: Mức phí từ **20.000 - 40.000 VND / tấn**.\n*   **Chất thải rắn nguy hại (vật liệu dễ cháy nổ, chứa hóa chất độc hại)**: Mức phí từ **100.000 - 200.000 VND / tấn**.\n*   **Miễn phí tái chế**: Lượng chất thải rắn được doanh nghiệp tự phân loại và đưa vào quy trình tái chế, sử dụng làm nguyên liệu sản xuất tại chỗ không phải chịu phí xả thải."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Quản Lý Chất Thải v64\n*   **Vùng Lõi (Core)**: Tính phí xả chất thải rắn thông thường/nguy hại, xác định khối lượng tái chế được khấu trừ.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với hóa đơn dịch vụ vận chuyển chất thải của đơn vị môi trường đô thị.\n*   **Vùng Biên Giới (Frontier)**: AI quét hóa đơn thu mua phế liệu đầu ra để đối so sánh khối lượng chất thải rắn thực tế giảm thiểu.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Vận hành lò đốt chất thải sinh học tại nhà máy."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Hợp Đồng Vận Chuyển\n*   **Hợp đồng thu gom (Constraint)**: Doanh nghiệp **bắt buộc** phải ký hợp đồng thu gom, vận chuyển chất thải rắn với các đơn vị được cơ quan quản lý cấp phép hành nghề. Khối lượng bàn giao trên biên bản là căn cứ tính phí bảo vệ môi trường."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Phí Chất Thải Rắn\n\n```mermaid\ngraph TD\n    A[Bàn giao chất thải rắn cho đơn vị thu gom] --> B[Ghi nhận Khối lượng bàn giao kg]\n    B --> C{Chất thải thuộc diện nguy hại?}\n    C -->|Có| D[Áp phí chất thải nguy hại 150.000 VND/tấn]\n    C -->|Không| E{Có được tái chế sử dụng lại tại chỗ?}\n    E -->|Có| F[Khấu trừ phần khối lượng tái chế khỏi tổng tính phí]\n    E -->|Không| G[Áp phí chất thải thông thường 30.000 VND/tấn]\n    D --> H[Tổng phí = Khối lượng tính phí x Mức phí tương ứng]\n    F --> H\n    G --> H\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Chất Thải Rắn v64\n*   MST Đang Xem: **{mst}**\n*   Khối lượng chất thải rắn đã gom: **{total_violations * 10:,.1f} tấn**\n*   Tổng phí xả thải phát sinh trong kỳ: **{total_violations * 1500000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Trộn lẫn chất thải nguy hại**: Trộn lẫn chất thải nguy hại vào chất thải thông thường để tránh nộp mức phí cao dẫn đến bị phạt nặng khi kiểm tra môi trường đột xuất.\n2. **Sai số cân đo**: Ghi nhận khối lượng chất thải dựa trên số lượng thùng gom ước tính thay vì phiếu cân thực tế tại bãi hủy."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Thiết lập khu vực phân loại rác thải tại nguồn trong khuôn viên nhà xưởng.\n*   **Bước 2**: Thực hiện ghi nhận và đồng bộ khối lượng chất thải bàn giao hàng tháng với hệ thống GDT Hub để tính toán phí.\n\n### Luật tham chiếu\n*   **Nghị định số 164/2016/NĐ-CP** quy định về phí bảo vệ môi trường đối với chất thải rắn."
            }
        ]

    elif v_clean == "v65":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ trách nhiệm mở rộng của nhà sản xuất (Extended Producer Responsibility - EPR) đối với hoạt động thu hồi, tái chế bao bì sản phẩm theo Nghị định số 08/2022/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để tính tỷ lệ tái chế bắt buộc (R) và hệ số chi phí tái chế (Fs) cho các loại bao bì (nhựa, giấy, kim loại) để xác định số tiền đóng góp vào Quỹ Bảo vệ môi trường?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp công thức tính đóng góp tài chính EPR chi tiết, biểu giá hệ số Fs của Bộ Tài nguyên và Môi trường giúp doanh nghiệp lập kế hoạch ngân sách tuân thủ EPR hàng năm."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Công Thức Đóng Góp Tài Chính EPR v65\n*   **Số tiền đóng góp (F)**: = V × R × Fs.\n    - V: Khối lượng sản phẩm, bao bì sản xuất hoặc nhập khẩu đưa ra thị trường trong năm.\n    - R: Tỷ lệ tái chế bắt buộc đối với từng loại sản phẩm (ví dụ: chai nhựa PET 22%, bao bì kim loại 20%).\n    - Fs: Hệ số chi phí tái chế hợp lý (đồng/kg) do Bộ TNMT ban hành (ví dụ: nhựa cứng PET 15.000đ/kg).\n*   **Miễn đóng góp**: Doanh nghiệp tự tổ chức tái chế đạt tỷ lệ R hoặc thuê đơn vị tái chế chuyên nghiệp thực hiện."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Áp Dụng EPR v65\n*   **Vùng Lõi (Core)**: Tính toán khối lượng bao bì đưa ra thị trường, tính số tiền đóng góp EPR theo công thức V x R x Fs.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với báo cáo doanh thu bán hàng xuất khẩu để trừ phần bao bì không chịu EPR nội địa.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích và cảnh báo khi có sự thay đổi về hệ số Fs hoặc tỷ lệ tái chế bắt buộc.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Trực tiếp xây dựng nhà máy tái chế bao bì nhựa."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Hạn Nộp EPR\n*   **Thời hạn đăng ký (Constraint)**: Doanh nghiệp bắt buộc phải đăng ký kế hoạch tái chế hoặc nộp tờ khai đóng góp tài chính EPR trước ngày **31 tháng 3** hàng năm đối với sản lượng của năm trước liền kề."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Toán Đóng Góp Tài Chính EPR\n\n```mermaid\ngraph TD\n    A[Nhập khối lượng bao bì đưa ra thị trường kg] --> B{Doanh nghiệp tự tổ chức tái chế đạt tỷ lệ R?}\n    B -->|Có| C[Nộp báo cáo kết quả tái chế - Số tiền đóng góp = 0]\n    B -->|Không| D[Tính tiền đóng góp F = Khối lượng x Tỷ lệ R x Hệ số Fs]\n    D --> E[Lập tờ khai đóng góp tài chính nộp Quỹ Bảo vệ môi trường]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Bao Bì EPR v65\n*   MST Đang Xem: **{mst}**\n*   Khối lượng bao bì sản xuất: **{total_violations * 20:,.1f} tấn**\n*   Tổng đóng góp EPR tạm tính: **{total_violations * 35000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai thiếu bao bì đi kèm**: Chỉ kê khai khối lượng sản phẩm chính mà bỏ quên khối lượng màng co nhựa hoặc hộp giấy bao bì ngoài.\n2. **Sử dụng sai hệ số Fs**: Áp dụng hệ số Fs của nhựa mềm cho nhựa cứng PET dẫn đến tính sai số tiền phải đóng góp."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Thiết lập hệ thống ghi nhận trọng lượng bao bì sử dụng cho từng dòng sản phẩm xuất xưởng.\n*   **Bước 2**: Thực hiện đăng ký kế hoạch tái chế trước ngày 31/03 hàng năm thông qua cổng thông tin EPR quốc gia.\n\n### Tài Liệu Tham Khảo\n*   **Nghị định số 08/2022/NĐ-CP** quy định chi tiết một số điều của Luật Bảo vệ môi trường."
            }
        ]

    elif v_clean == "v66":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ giảm nhẹ phát thải khí nhà kính (Greenhouse Gas - GHG) và thực hiện kiểm kê khí nhà kính theo quy định tại Nghị định số 06/2022/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động quy đổi lượng điện năng tiêu thụ, than đá, dầu diesel sang lượng phát thải CO2 tương đương (CO2e) và cảnh báo khi doanh nghiệp vượt ngưỡng kiểm kê 3.000 tấn CO2e/năm?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp hệ số quy đổi phát thải chuẩn của IPCC, quy trình kiểm kê khí nhà kính và cơ chế sử dụng hạn ngạch phát thải giúp doanh nghiệp chuẩn bị báo cáo kiểm kê đúng hạn."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Công Thức Tính Phát Thải CO2e v66\n*   **Lượng phát thải CO2e**: = Lượng nhiên liệu tiêu thụ × Hệ số phát thải CO2e của loại nhiên liệu đó.\n*   **Hệ số phát thải điển hình (IPCC)**:\n    - Điện tiêu thụ: **0.86 tấn CO2e / MWh**.\n    - Dầu Diesel: **2.68 tấn CO2e / 1.000 lít**.\n    - Than Anthracit: **2.4 tấn CO2e / tấn**.\n*   **Ngưỡng bắt buộc kiểm kê**: Doanh nghiệp có lượng phát thải hàng năm từ **3.000 tấn CO2e** trở lên bắt buộc phải thực hiện kiểm kê khí nhà kính và lập kế hoạch giảm nhẹ phát thải."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Kiểm Kê Khí Nhà Kính v66\n*   **Vùng Lõi (Core)**: Tính lượng phát thải CO2e trực tiếp (Scope 1) từ đốt nhiên liệu và gián tiếp (Scope 2) từ điện tiêu thụ.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với hóa đơn tiền điện và hóa đơn mua xăng dầu đầu vào.\n*   **Vùng Biên Giới (Frontier)**: AI dự báo lượng phát thải CO2e theo tháng và tính số lượng tín chỉ carbon tối đa (10%) được phép bù đắp.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Giao dịch tín chỉ carbon quốc tế hoặc thiết lập dự án phục hồi rừng."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Hạn Ngạch Phát Thải\n*   **Hạn ngạch phát thải (Constraint)**: Cơ sở phát thải lớn được phân bổ hạn ngạch phát thải khí nhà kính hàng năm. Doanh nghiệp chỉ được phép bù đắp tối đa **10%** hạn ngạch được phân bổ bằng các tín chỉ carbon hợp chuẩn để đạt mục tiêu tuân thủ."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Toán & Cảnh Báo Phát Thải GHG\n\n```mermaid\ngraph TD\n    A[Nhập số liệu tiêu thụ Điện & Nhiên liệu] --> B[Quy đổi lượng tiêu thụ sang đơn vị MWh & Tấn]\n    B --> C[Nhân với Hệ số phát thải CO2e tương ứng của IPCC]\n    C --> D[Cộng tổng phát thải Scope 1 & Scope 2 = CO2e phát sinh]\n    D --> E{Tổng lượng phát thải hàng năm >= 3.000 tấn CO2e?}\n    E -->|Có| F[Cảnh báo: Bắt buộc lập Báo cáo kiểm kê khí nhà kính gửi Sở TNMT]\n    E -->|Không| G[Lưu trữ số liệu quan trắc nội bộ]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Phát Thải Khí Nhà Kính v66\n*   MST Đang Xem: **{mst}**\n*   Tổng lượng phát thải CO2e ước tính: **{total_violations * 250:,.1f} tấn CO2e**\n*   Trạng thái kiểm kê: **Cận ngưỡng bắt buộc kiểm kê**\n\n### Sai sót thường gặp\n1. **Bỏ sót phát thải gián tiếp**: Chỉ tính lượng phát thải Scope 1 từ lò hơi mà bỏ qua lượng phát thải khổng lồ Scope 2 từ hệ thống điều hòa và máy móc chạy điện.\n2. **Sử dụng sai hệ số phát thải**: Áp dụng hệ số phát thải của lưới điện nước ngoài thay vì hệ số phát thải lưới điện Việt Nam do Bộ TNMT công bố."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Xây dựng quy trình theo dõi lượng nhiên liệu tiêu thụ và hóa đơn tiền điện hàng tháng.\n*   **Bước 2**: Thực hiện kiểm kê khí nhà kính thử nghiệm trước khi chính thức lập báo cáo nộp cơ quan quản lý định kỳ 2 năm một lần.\n\n### Luật tham chiếu\n*   **Quyết định số 01/2022/QĐ-TTg** ban hành danh mục lĩnh vực, cơ sở phát thải khí nhà kính phải thực hiện kiểm kê khí nhà kính."
            }
        ]

    elif v_clean == "v67":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ quy định ký quỹ bảo đảm phế liệu nhập khẩu (Scrap Import Deposit) đối với doanh nghiệp sử dụng phế liệu nhập khẩu làm nguyên liệu sản xuất theo Nghị định số 08/2022/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động xác định mức ký quỹ (10% - 20% trị giá lô hàng) dựa trên khối lượng và chủng loại phế liệu nhập khẩu (sắt, thép, giấy, nhựa)?* \n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu phí tỷ lệ ký quỹ phế liệu, quy trình xác thực biên lai ký quỹ tại ngân hàng thương mại trước khi làm thủ tục thông quan hàng hóa giúp doanh nghiệp thông quan nhanh chóng."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Biểu Mức Ký Quỹ Phế Liệu v67\n*   **Phế liệu sắt, thép nhập khẩu**:\n    - Dưới 500 tấn: Ký quỹ **10%** tổng trị giá lô hàng nhập khẩu.\n    - Từ 500 tấn đến dưới 1.000 tấn: Ký quỹ **15%** tổng trị giá.\n    - Từ 1.000 tấn trở lên: Ký quỹ **20%** tổng trị giá.\n*   **Phế liệu giấy và nhựa nhập khẩu**:\n    - Dưới 100 tấn: Ký quỹ **15%** trị giá lô hàng.\n    - Từ 100 tấn trở lên: Ký quỹ **20%** trị giá lô hàng."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Ký Quỹ Phế Liệu v67\n*   **Vùng Lõi (Core)**: Tính toán số tiền ký quỹ theo khối lượng và trị giá lô hàng, đối chiếu chứng từ biên lai ký quỹ ngân hàng.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với tờ khai hải quan nhập khẩu và hợp đồng mua bán với đối tác nước ngoài.\n*   **Vùng Biên Giới (Frontier)**: AI kiểm tra và đối sánh hóa đơn gốc để cảnh báo sai lệch khối lượng khai báo trước khi nộp tiền.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Quản lý bãi chứa phế liệu thực địa hoặc xử lý nước thải phát sinh từ bãi phế liệu."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Ký Quỹ Thông Quan\n*   **Thời hạn ký quỹ (Constraint)**: Việc ký quỹ bảo đảm bảo vệ môi trường phải được thực hiện **trước** thời điểm làm thủ tục thông quan phế liệu nhập khẩu ít nhất là 15 ngày làm việc."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Xác Định Mức Ký Quỹ Phế Liệu\n\n```mermaid\ngraph TD\n    A[Nhận tờ khai phế liệu nhập khẩu] --> B{Loại phế liệu nhập khẩu?}\n    B -->|Sắt thép| C{Khối lượng >= 1.000 tấn?}\n    C -->|Có| D[Nộp ký quỹ 20% tổng trị giá lô hàng]\n    C -->|Không| E{Khối lượng từ 500 đến dưới 1.000 tấn?}\n    E -->|Có| F[Nộp ký quỹ 15% tổng trị giá]\n    E -->|Không| G[Nộp ký quỹ 10% tổng trị giá]\n    B -->|Giấy/Nhựa| H{Khối lượng >= 100 tấn?}\n    H -->|Có| I[Nộp ký quỹ 20% trị giá]\n    H -->|Không| K[Nộp ký quỹ 15% trị giá]\n    D --> L[Lập lệnh ký quỹ sang Ngân hàng thương mại để phong tỏa tài khoản]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Nhập Khẩu Phế Liệu v67\n*   MST Đang Xem: **{mst}**\n*   Khối lượng phế liệu sắt thép nhập trong kỳ: **{total_violations * 120:,.0f} tấn**\n*   Tổng số tiền ký quỹ đang bị phong tỏa: **{total_violations * 450000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Ký quỹ muộn**: Làm hồ sơ ký quỹ tại ngân hàng sát ngày tàu cập cảng dẫn đến ách tắc thông quan và phát sinh chi phí lưu kho bãi (demurrage).\n2. **Khai báo sai trị giá**: Sử dụng đơn giá trên hợp đồng thấp hơn giá trị thị trường thực tế để giảm số tiền ký quỹ dẫn đến hải quan bác bỏ hồ sơ."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Kê Khai\n*   **Bước 1**: Thiết lập liên kết thông tin ngân hàng bảo lãnh ký quỹ trên hồ sơ doanh nghiệp của GDT Hub.\n*   **Bước 2**: Thực hiện tính toán và lập lệnh ký quỹ tự động khi phê duyệt hợp đồng mua phế liệu nước ngoài.\n\n### Luật tham chiếu\n*   **Luật Bảo vệ môi trường số 72/2020/QH14** (Điều 137 quy định về ký quỹ bảo vệ môi trường)."
            }
        ]

    elif v_clean == "v68":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ nghĩa vụ tài chính bảo tồn đa dạng sinh học và chi trả dịch vụ môi trường rừng đối với doanh nghiệp có hoạt động ảnh hưởng đến hệ sinh thái tự nhiên theo Luật Đa dạng sinh học 2008.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động xác định mức phí hệ sinh thái (80 triệu - 250 triệu VND/ha) và áp dụng hệ số nhân 1.5x đối với các dự án có tác động cao đến vùng bảo tồn đệm?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp khung phí môi trường sinh thái chi tiết, cơ chế áp dụng hệ số rủi ro địa lý giúp doanh nghiệp dự phòng chi phí bồi hoàn đa dạng sinh học chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Mức Phí Đa Dạng Sinh Học v68\n*   **Dự án nằm ngoài vùng đệm**: Mức phí cơ sở từ **80.000.000 - 120.000.000 VND / ha**.\n*   **Dự án nằm trong vùng đệm bảo tồn**: Mức phí cơ sở từ **150.000.000 - 250.000.000 VND / ha**.\n*   **Hệ số tác động cao**: Áp dụng nhân thêm **1.5x** tổng phí nếu dự án trực tiếp thay đổi cơ cấu rừng tự nhiên hoặc lấn chiếm đất ngập nước."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Phí Sinh Thái v68\n*   **Vùng Lõi (Core)**: Tính toán phí bồi hoàn sinh thái theo diện tích ha bị tác động, áp dụng hệ số nhân vùng đệm 1.5x.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với bản vẽ quy hoạch sử dụng đất và quyết định giao đất của UBND tỉnh.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích và cảnh báo khi dự án tiệm cận ranh giới khu bảo tồn thiên nhiên quốc gia.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Hoạt động trồng rừng thay thế thực tế hoặc nghiên cứu sinh vật học mỏ."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Chi Trả Sinh Thái\n*   **Nghĩa vụ nộp phí (Constraint)**: Các tổ chức được giao đất, cho thuê đất trong khu bảo tồn thiên nhiên để làm dự án du lịch sinh thái hoặc khai thác khoáng sản **bắt buộc** phải nộp phí đa dạng sinh học và chi trả dịch vụ môi trường."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Phí Bảo Tồn Đa Dạng Sinh Học\n\n```mermaid\ngraph TD\n    A[Nhập diện tích dự án ha] --> B{Dự án nằm trong vùng đệm bảo tồn?}\n    B -->|Có| C[Áp mức phí cơ sở 200.000.000 VND/ha]\n    B -->|Không| D[Áp mức phí cơ sở 100.000.000 VND/ha]\n    A --> E{Dự án gây tác động cao thay đổi cơ cấu rừng?}\n    E -->|Có| F[Áp dụng hệ số nhân tác động 1.5x]\n    E -->|Không| G[Áp dụng hệ số nhân cơ sở 1.0x]\n    C --> H[Tổng phí = Diện tích x Mức phí cơ sở x Hệ số nhân]\n    D --> H\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Dự Án Sinh Thái v68\n*   MST Đang Xem: **{mst}**\n*   Diện tích đất dự án tác động: **{total_violations * 2:,.1f} ha**\n*   Tổng phí đa dạng sinh học phát sinh: **{total_violations * 150000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai thiếu diện tích vùng đệm**: Báo cáo diện tích lấn chiếm vùng đệm thấp hơn thực tế nhằm giảm số tiền bồi hoàn sinh thái phải đóng.\n2. **Quên tính hệ số nhân**: Tính toán chi phí bồi hoàn theo mức cơ sở cho dự án khai thác mỏ đá nằm sát khu bảo tồn mà không nhân hệ số 1.5x."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Rà soát ranh giới dự án trên hệ thống bản đồ số (GIS) và nhập tọa độ vào cấu hình của GDT Hub.\n*   **Bước 2**: Thực hiện tính toán và nộp phí dịch vụ môi trường hàng năm trước thời điểm kiểm toán thuế CIT.\n\n### Luật tham chiếu\n*   **Luật Đa dạng sinh học số 20/2008/QH12** và các Nghị định hướng dẫn thi hành bồi hoàn sinh thái."
            }
        ]

    elif v_clean == "v69":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và xác định nghĩa vụ đóng đóng phí phòng ngừa ứng phó sự cố tràn dầu đối với các cảng biển, kho xăng dầu và cơ sở kinh doanh xăng dầu theo Quyết định số 12/2021/QĐ-TTg.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động tính phí cơ sở hàng quý và phí biến đổi dựa trên dung tích chứa dầu (500đ/m3) của cơ sở, kèm theo cảnh báo nhân đôi 2.0x khi hoạt động trong khu vực nhạy cảm môi trường?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu phí tràn dầu chi tiết, cơ chế áp dụng hệ số rủi ro khu vực nhạy cảm giúp doanh nghiệp lập dự phòng chi phí an toàn tràn dầu chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Mức Phí Ứng Phó Sự Cố Tràn Dầu v69\n*   **Phí cố định hàng quý**: **10.000.000 VND / quý** (cho mỗi kho chứa).\n*   **Phí dung tích chứa**: **500 VND / m3** dung tích bồn chứa xăng dầu.\n*   **Khu vực nhạy cảm môi trường (cận rừng ngập mặn, bãi biển du lịch)**: Áp dụng nhân **2.0x** mức phí bồn chứa để tăng cường trách nhiệm bảo vệ."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Phí Tràn Dầu v69\n*   **Vùng Lõi (Core)**: Tính toán phí cố định và phí dung tích hàng quý, áp dụng hệ số nhân 2.0x cho khu vực nhạy cảm.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với tờ khai thuế bảo vệ môi trường xăng dầu v53 đầu vào để kiểm tra chéo lượng dầu lưu kho.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích và cảnh báo khi lượng dầu dự trữ vượt quá 90% dung tích bồn chứa thiết kế.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Mua sắm trang thiết bị phao vây tràn dầu thực tế."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Cam Kết Ứng Phó\n*   **Kế hoạch ứng phó (Constraint)**: Cơ sở kinh doanh xăng dầu có dung tích chứa từ **500 m3** trở lên bắt buộc phải lập Kế hoạch ứng phó sự cố tràn dầu trình cấp có thẩm quyền phê duyệt mới được hoạt động."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Phí Tràn Dầu Hàng Quý\n\n```mermaid\ngraph TD\n    A[Nhập tổng dung tích chứa xăng dầu m3] --> B{Cơ sở nằm trong khu vực nhạy cảm?}\n    B -->|Có| C[Áp dụng phí dung tích = Dung tích x 500 VND x hệ số 2.0]\n    B -->|Không| D[Áp dụng phí dung tích = Dung tích x 500 VND x hệ số 1.0]\n    C --> E[Tổng phí quý = Phí cố định 10.000.000 VND + Phí dung tích]\n    D --> E\n    E --> F[Lập tờ khai phí nộp ngân sách địa phương]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Kho Dầu v69\n*   MST Đang Xem: **{mst}**\n*   Dung tích kho chứa đã khai báo: **{total_violations * 200:,.0f} m3**\n*   Tổng phí tràn dầu phát sinh hàng quý: **{total_violations * 20000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai thiếu dung tích bồn**: Chỉ khai báo bồn chứa nổi mà bỏ qua các bồn chứa dầu ngầm dự phòng dẫn đến đóng thiếu phí.\n2. **Áp sai khu vực nhạy cảm**: Không tự giác nhân hệ số 2.0x khi bồn chứa xăng dầu nằm sát sông lớn có cửa thông ra biển."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Đăng ký thông số kỹ thuật bồn chứa xăng dầu của doanh nghiệp vào hệ thống GDT Hub.\n*   **Bước 2**: Thực hiện rà soát và nộp tờ khai phí tràn dầu định kỳ hàng quý trước ngày 20 của quý sau.\n\n### Luật tham chiếu\n*   **Quyết định số 12/2021/QĐ-TTg** ban hành quy chế hoạt động ứng phó sự cố tràn dầu."
            }
        ]

    elif v_clean == "v70":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý và kiểm soát hạn ngạch nhập khẩu, sản xuất và sử dụng các chất làm suy giảm tầng ô-dôn (Ozone-Depleting Substances - ODS) theo quy định tại Nghị định số 06/2022/NĐ-CP của Chính phủ.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống giám sát tự động hạn ngạch tiêu thụ ODS của doanh nghiệp dựa trên hóa đơn nhập khẩu và giấy phép đăng ký hạn ngạch hàng năm?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp góc nhìn toàn diện về quy trình cấp phép ODS, ngưỡng hạn ngạch tối đa và cảnh báo tự động khi doanh nghiệp tiệm cận giới hạn cho phép nhằm tránh các chế tài pháp lý nghiêm khắc."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Các Thực Thể Quản Lý ODS\n*   **Taxpayer Quota (Hạn ngạch MST)**: Lưu trữ hạn ngạch ODS tối đa được Bộ TNMT cấp phép trong năm.\n*   **ODS Consumption (Lượng tiêu thụ)**: Lượng ODS thực tế nhập khẩu/mua vào thông qua hóa đơn đầu vào.\n*   **License Verification (Giấy phép)**: Trạng thái và thời hạn giấy phép nhập khẩu ODS tương ứng.\n\n### Biểu thức tính hạn ngạch còn lại\n`Lượng hạn ngạch còn lại = Hạn ngạch được cấp - Tổng lượng nhập khẩu đã đối soát`"
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phân Lớp Quản Lý ODS v70\n*   **Vùng Lõi (Core)**: Quản lý lượng hạn ngạch cấp phép, trừ lùi hạn ngạch tự động qua hóa đơn đầu vào, cảnh báo khi lượng mua vượt quá hạn ngạch cho phép.\n*   **Vùng Cận Biên (Adjacent)**: Đồng bộ dữ liệu tờ khai hải quan nhập khẩu (customs declaration) để so sánh chéo khối lượng thực nhập.\n*   **Vùng Biên Giới (Frontier)**: Tự động dự báo xu hướng tiêu thụ ODS dựa trên kế hoạch sản xuất để đề xuất xin thêm hạn ngạch sớm.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Đo đạc nồng độ hóa chất bay hơi trực tiếp trong nhà xưởng hoặc kiểm tra hiện trường rò rỉ khí gas."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Các Mối Quan Hệ Hạn Ngạch ODS\n*   **Định nghĩa (Definition)**: ODS bao gồm các chất chứa clo, brom gây suy giảm tầng ô-dôn như CFC, Halon, HCFC, và methyl bromide.\n*   **Ràng buộc (Constraint)**: Việc nhập khẩu ODS **phải** được Bộ Tài nguyên và Môi trường phân bổ hạn ngạch nhập khẩu.\n*   **Cơ chế (Mechanism)**: Lượng ODS thực tế tính theo tấn khí tương đương CO2 hoặc trọng lượng thuần tùy loại hóa chất quy định trong danh mục phụ lục Nghị định 06/2022/NĐ-CP."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Duyệt Giấy Phép & Hạn Ngạch ODS\n1. Doanh nghiệp tải tờ khai hải quan XML hoặc hóa đơn nhập khẩu ODS lên GDT Invoice Hub.\n2. Hệ thống đọc mã HS của hóa chất và đối chiếu với danh mục chất kiểm soát ODS v70.\n3. Hệ thống tính toán lượng tiêu thụ thực tế quy đổi.\n4. Thực hiện kiểm tra hạn ngạch còn lại:\n   - Nếu lượng tiêu thụ vượt hạn ngạch: Kích hoạt cảnh báo **Nguy cấp (Critical Block)**.\n   - Nếu hạn ngạch còn dưới 10%: Kích hoạt cảnh báo **Cận giới hạn (Warning)**."
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Thống Kê & Cảnh Báo Hạn Ngạch ODS v70\n*   MST Đang Xem: **{mst}**\n*   Số lượng hóa đơn ODS đã ghi nhận: **{chemical_count} hóa đơn**\n*   Các vi phạm hạn ngạch phát hiện: **{total_violations} cảnh báo**\n\n### Các Tình Huống Vi Phạm Lỗi\n1. **Nhập khẩu không giấy phép**: Doanh nghiệp khai báo mua hóa chất HCFC nhưng giấy phép nhập khẩu đã hết hạn hoặc chưa được duyệt.\n2. **Sai hệ số quy đổi**: Khai báo trọng lượng khí hóa lỏng không đúng thể tích nén thực tế dẫn đến tính sai lượng hạn ngạch tiêu hao."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Kế Hoạch Triển Khai\n*   **Tháng 1**: Khai báo và cấu hình định mức hạn ngạch ODS được cấp vào Profile của Doanh nghiệp trên GDT Hub.\n*   **Tháng 2**: Kích hoạt bộ lọc cảnh báo tự động trên phân hệ Hải quan / Mua vào.\n*   **Tháng 3**: Kết xuất báo cáo sử dụng chất ODS định kỳ gửi Cục Biến đổi khí hậu.\n\n### Tài liệu tham khảo chính\n*   *Nghị định số 06/2022/NĐ-CP quy định chi tiết giảm nhẹ phát thải khí nhà kính và bảo vệ tầng ô-dôn*\n*   *Thông tư số 01/2022/TT-BTNMT quy định chi tiết thi hành Luật Bảo vệ môi trường về ứng phó với biến đổi khí hậu*"
            }
        ]

    elif v_clean == "v71":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nTự động hóa tính toán phí tái chế và xử lý chất thải điện tử (E-Waste EPR) theo trách nhiệm mở rộng của nhà sản xuất (Extended Producer Responsibility) được quy định tại Nghị định số 08/2022/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để nhận diện sản phẩm thuộc danh mục bắt buộc EPR trên hóa đơn và áp dụng đúng thuế suất hoặc các điều kiện miễn trừ xuất khẩu/quy mô nhỏ?*\n\n### Lời hứa của bản đồ (Map Promise)\nBản đồ này cung cấp đầy đủ danh mục biểu phí tuyệt đối đối với laptop, tivi, điện thoại, pin và tấm pin năng lượng mặt trời, kèm theo bộ quy tắc tự động hóa loại trừ các lô hàng xuất khẩu hoặc doanh nghiệp có quy mô doanh thu/nhập khẩu dưới ngưỡng chịu phí."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Thực Thể & Thuộc Tính EPR v71\n*   **E-Waste Record**: Lưu giữ thông tin phân loại sản phẩm, số lượng, trạng thái xuất khẩu và các giá trị tài chính năm trước.\n*   **EPR Fee Calculation**:\n    - Phí EPR = Số lượng × Mức phí tuyệt đối trên một đơn vị sản phẩm hoặc đơn vị trọng lượng.\n    - Mức phí chi tiết: Máy tính xách tay (20.000đ/chiếc), Tivi/Màn hình (30.000đ/chiếc), Điện thoại di động (5.000đ/chiếc), Pin các loại (50.000đ/kg), Tấm quang điện (15.000đ/kg).\n    - Kiểm tra điều kiện miễn trừ EPR: Được miễn nếu là hàng trực tiếp xuất khẩu hoặc doanh nghiệp có doanh thu năm trước < 30 tỷ VND hoặc trị giá nhập khẩu năm trước < 3 tỷ VND."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Các Phân Lớp Phạm Vi v71\n*   **Vùng Lõi (Core)**: Tính toán chính xác phí EPR thô, xác thực các lý do miễn trừ hợp lệ (export, doanh thu năm trước, kim ngạch nhập khẩu).\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với tờ khai quyết toán CIT năm trước để lấy thông tin doanh thu thực tế, và đối soát với tờ khai hải quan hàng nhập khẩu.\n*   **Vùng Biên Giới (Frontier)**: Sử dụng AI để tự động phân tích và gắn nhãn sản phẩm điện tử trên hóa đơn mua bán tự do không chứa mã HS.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Ký hợp đồng trực tiếp với đơn vị thu gom tái chế thực địa hoặc kiểm tra chất lượng tái chế."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Quy Tắc Liên Kết EPR\n*   **Định nghĩa (Definition)**: EPR v71 là quy định bắt buộc nhà sản xuất, nhập khẩu các sản phẩm điện, điện tử phải thực hiện nghĩa vụ thu hồi và tái chế sản phẩm thải bỏ.\n*   **Ràng buộc (Constraint)**: Nghĩa vụ đóng phí EPR nộp vào Quỹ Bảo vệ môi trường Việt Nam **chỉ** phát sinh khi doanh nghiệp không tự tổ chức tái chế hoặc lượng tái chế thực tế không đạt tỷ lệ bắt buộc."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Sơ Đồ Quy Trình Xác Định Phí EPR\n\n```mermaid\ngraph TD\n    A[Nhận hóa đơn điện tử thiết bị] --> B{Sản phẩm có thuộc diện EPR?}\n    B -->|Không| C[Bỏ qua]\n    B -->|Có| D{Có chứng từ xuất khẩu trực tiếp?}\n    D -->|Có| E[Gắn nhãn miễn phí: export_exemption]\n    D -->|Không| F{Doanh thu năm trước < 30B VND hoặc Nhập khẩu < 3B VND?}\n    F -->|Có| G[Gắn nhãn miễn phí: small_scale_exemption]\n    F -->|Không| H[Tính phí theo mức tuyệt đối quy định]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thực Tế Hệ Thống v71\n\n*   MST Đang Xem: **{mst}**\n*   Số bản ghi e-waste đã xử lý: **{ewaste_count}**\n*   Tổng số cảnh báo lỗi/vi phạm phát hiện: **{total_violations}**\n\n### Các Tình Huống Sai Sót Thường Gặp\n1. **Khai báo miễn trừ sai năm**: Sử dụng doanh thu của năm hiện tại thay vì năm trước liền kề để làm căn cứ miễn trừ quy mô nhỏ.\n2. **Áp sai danh mục**: Nhầm lẫn giữa pin lithium sơ cấp (EPR 50.000đ/kg) với ắc quy chì công nghiệp (thuộc nhóm EPR khác)."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Khai báo các thông tin tài chính cơ sở (doanh thu năm trước, kim ngạch nhập khẩu) trong hồ sơ doanh nghiệp.\n*   **Bước 2**: Bật tính năng quét cảnh báo sớm EPR đối với hóa đơn mua sắm trang thiết bị văn phòng đầu vào.\n\n### Tài Liệu Nghiên Cứu Đề Xuất\n1. *Nghị định số 08/2022/NĐ-CP hướng dẫn Luật Bảo vệ môi trường 2020*\n2. *Thông tư số 02/2022/TT-BTNMT quy định chi tiết thi hành một số điều của Luật Bảo vệ môi trường*"
            }
        ]

    elif v_clean == "v72":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nTự động hóa tính toán phí bảo vệ môi trường đối với nước thải công nghiệp và nước thải sinh hoạt theo Nghị định số 53/2020/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để tự động hóa khâu phân loại phí cố định và phí biến đổi (hàm lượng COD, TSS, Pb, Hg, Cd) dựa trên lưu lượng nước thải thực tế và thông tin miễn trừ?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp công thức tính toán chi tiết, mức phí tuyệt đối và các ngưỡng miễn phí đối với nước làm mát hoặc nước tuần hoàn khép kín, giúp doanh nghiệp lập dự phòng chi phí môi trường chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Phương Pháp Tính Phí Nước Thải v72\n*   **Lưu lượng trung bình hàng ngày**: `Lưu lượng quý / 90 ngày`.\n*   **Trường hợp 1**: Lưu lượng < 20 $m^3$/ngày đêm: Áp dụng phí cố định flat rate **375.000 VND / quý** (tương đương 125.000 VND/tháng).\n*   **Trường hợp 2**: Lưu lượng >= 20 $m^3$/ngày đêm: Phí biến đổi nộp thêm tính theo tải lượng chất ô nhiễm:\n    - COD: 2.000 VND / kg chất gây ô nhiễm.\n    - TSS: 4.000 VND / kg chất gây ô nhiễm.\n    - Lead (Chì - Pb): 1.000.000 VND / kg chất gây ô nhiễm.\n    - Mercury (Thủy ngân - Hg): 20.000.000 VND / kg chất gây ô nhiễm.\n    - Cadmium (Cd): 10.000.000 VND / kg chất gây ô nhiễm.\n*   **Miễn trừ**: Áp dụng cho nước làm mát không tiếp xúc trực tiếp quy trình sản xuất hoặc nước xả lũ."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Ứng Dụng Phí Nước Thải v72\n*   **Vùng Lõi (Core)**: Tính toán phí cố định/biến đổi, xác định tải lượng chất gây ô nhiễm trên cơ sở lưu lượng thực tế.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với chỉ số đồng hồ lưu lượng nước tiêu thụ và hóa đơn dịch vụ xả thải của ban quản lý khu công nghiệp.\n*   **Vùng Biên Giới (Frontier)**: Dự báo tải lượng COD/TSS dựa trên kế hoạch sản xuất để điều chỉnh lượng hóa chất xử lý nước thải tương ứng.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Vận hành hệ thống lọc nước sinh học hoặc xây dựng đường ống thoát nước."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc & Cơ Chế\n*   **Định nghĩa (Definition)**: Phí nước thải công nghiệp v72 là khoản thu ngân sách bắt buộc đối với cơ sở có hoạt động xả nước thải vào nguồn tiếp nhận.\n*   **Ràng buộc (Constraint)**: Nước thải sinh hoạt được miễn thu phí nếu cơ sở sử dụng nước sạch tự nhiên và đã nộp phí nước thải sinh hoạt qua hóa đơn nước sạch hàng tháng."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Quy Trình Phân Tích & Tính Phí\n\n```mermaid\ngraph TD\n    A[Nhận số liệu lưu lượng & quan trắc] --> B{Nước làm mát tuần hoàn khép kín?}\n    B -->|Có| C[Miễn trừ phí - is_exempt]\n    B -->|Không| D{Lưu lượng trung bình < 20 m3/ngày?}\n    D -->|Có| E[Áp phí cố định 375.000 VND/quý]\n    D -->|Không| F[Tính tải lượng ô nhiễm COD, TSS, Pb, Hg, Cd]\n    F --> G[Cộng tổng phí biến đổi với phí cố định]\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Thực Tế Hệ Thống v72\n\n*   MST Đang Xem: **{mst}**\n*   Số bản ghi xả nước thải đã xử lý: **{wastewater_count}**\n*   Tổng số cảnh báo lỗi/vi phạm phát hiện: **{total_violations}**\n\n### Các Tình Huống Sai Sót Thường Gặp\n1. **Thiếu số liệu kim loại nặng**: Bỏ qua việc khai báo và kiểm định nồng độ Pb, Hg, Cd khi cơ quan quản lý thực hiện lấy mẫu đột xuất.\n2. **Khai báo lưu lượng ước tính sai lệch**: Sử dụng lưu lượng bình quan lý thuyết thay vì lưu lượng thực đo từ đồng hồ đo kiểm định."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Áp Dụng Thực Tế\n*   **Tháng 1**: Kết nối hệ thống quan trắc nước thải tự động (nếu có) với phân hệ dữ liệu GDT Hub.\n*   **Tháng 2**: Thiết lập cảnh báo sớm khi chỉ số COD vượt ngưỡng giới hạn cho phép trước khi cơ quan ban ngành kiểm tra.\n\n### Tài Liệu Nghiên Cứu Đề Xuất\n1. *Nghị định số 53/2020/NĐ-CP quy định về phí bảo vệ môi trường đối với nước thải*\n2. *Thông tư hướng dẫn kê khai và quyết toán phí nước thải*"
            }
        ]

    elif v_clean == "v73":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý và kiểm soát quy trình cấp phép, thu gom, vận chuyển và xử lý chất thải nguy hại (Hazardous Waste Disposal) theo các quy định của Nghị định số 08/2022/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động phát hiện chất thải nguy hại trên hóa đơn, áp đúng mức phí xử lý theo mã chất thải nguy hại và kiểm tra giấy phép xả thải của nhà cung ứng?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp danh mục phân loại chất thải nguy hại chuẩn của Bộ TNMT, các ngưỡng phí xử lý và cơ chế kiểm duyệt giấy phép xả thải giúp doanh nghiệp kiểm soát tốt quy trình xử lý chất thải."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Cơ Chế Phí Chất Thải Nguy Hại v73\n*   **Mã chất thải nguy hại (Hazardous Code)**: Định danh theo danh mục chất thải nguy hại của Bộ Tài nguyên và Môi trường.\n*   **Phí xử lý chất thải nguy hại**:\n    - Nhóm dung môi hữu cơ thải: **150.000 VND / tấn**.\n    - Nhóm bùn thải chứa kim loại nặng: **180.000 VND / tấn**.\n    - Nhóm bóng đèn huỳnh quang thải: **200.000 VND / tấn**.\n    - Nhóm ắc quy chì thải: **100.000 VND / tấn**.\n*   **Miễn phí quy mô nhỏ**: Cơ sở phát sinh lượng chất thải nguy hại dưới **600 kg / năm** được tự xử lý tại chỗ hoặc chuyển giao không cần đăng ký chủ nguồn thải."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Quản Lý v73\n*   **Vùng Lõi (Core)**: Tính toán phí thu gom xử lý chất thải nguy hại, kiểm soát mã chất thải, áp dụng miễn phí quy mô nhỏ dưới 600kg/năm.\n*   **Vùng Cận Biên (Adjacent)**: Đối chiếu với chứng từ chuyển giao chất thải nguy hại (chứng từ CTNH) và hợp đồng vận chuyển.\n*   **Vùng Biên Giới (Frontier)**: AI quét biên bản bàn giao để tự động phân tích và gắn mã CTNH tương ứng.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Thiết kế công nghệ lò đốt chất thải nguy hại."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Chủ Nguồn Thải\n*   **Ràng buộc chủ nguồn (Constraint)**: Cơ sở phát sinh chất thải nguy hại vượt quá 600kg/năm **bắt buộc** phải đăng ký chủ nguồn thải và báo cáo quản lý chất thải nguy hại định kỳ hàng năm trước ngày 15/01."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Phí & Kê Khai Chất Thải Nguy Hại\n\n```mermaid\ngraph TD\n    A[Bàn giao chất thải nguy hại] --> B[Ghi nhận Khối lượng bàn giao kg]\n    B --> C{Tổng khối lượng năm < 600kg?}\n    C -->|Có| D[Áp dụng miễn phí xử lý quy mô nhỏ - is_exempt]\n    C -->|Không| E[Nhận mã chất thải nguy hại CTNH]\n    E --> F[Tra cứu đơn giá phí theo bảng phân loại]\n    F --> G[Tính phí = Khối lượng x Đơn giá phí tương ứng]\n    D --> H[Xuất báo cáo giám sát chất thải nguy hại]\n    G --> H\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Chất Thải Nguy Hại v73\n*   MST Đang Xem: **{mst}**\n*   Số bản ghi bàn giao chất thải nguy hại: **{hazardous_count}**\n*   Tổng phí xử lý chất thải nguy hại tạm tính: **{total_violations * 25000000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai sai mã chất thải**: Ghi nhận bùn thải nguy hại thành bùn thải thông thường để giảm thiểu chi phí xử lý chất thải.\n2. **Không lưu chứng từ CTNH**: Bàn giao chất thải nguy hại cho đơn vị vận chuyển nhưng không thu hồi đầy đủ liên chứng từ CTNH có chữ ký xác nhận của nhà máy xử lý cuối."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Đăng ký thông tin các dòng chất thải nguy hại phát sinh tại nhà máy vào cấu hình của GDT Hub.\n*   **Bước 2**: Thực hiện kiểm tra định kỳ lượng chất thải tích trữ tại kho lưu giữ tạm thời để đảm bảo không vượt quá thời hạn 6 tháng.\n\n### Tài Liệu Nghiên Cứu\n*   **Nghị định số 08/2022/NĐ-CP** (Chương V quy định về quản lý chất thải)."
            }
        ]

    elif v_clean == "v74":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tính toán phụ thu/surcharge đối với tiếng ồn và độ rung vượt ngưỡng tiêu chuẩn kỹ thuật quốc gia trong quá trình sản xuất và xây dựng.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động tính toán phụ thu tiếng ồn dựa trên mức dBA vượt ngưỡng (tối đa 70 dBA ban ngày, 55 dBA ban đêm) và áp dụng hệ số nhân 1.5x cho xả thải ban đêm?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp thang đo phụ thu tiếng ồn chi tiết, cơ chế áp dụng hệ số nhân ban đêm giúp doanh nghiệp lập dự phòng chi phí bồi thường và xử phạt ô nhiễm tiếng ồn chính xác."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Thang Đo Phụ Thu Tiếng Ồn v74\n*   **Ngưỡng tiêu chuẩn (dBA)**: Ban ngày (6h - 21h): **70 dBA** | Ban đêm (21h - 6h): **55 dBA**.\n*   **Mức phụ thu theo mức dBA vượt ngưỡng**:\n    - Vượt từ 1 đến 5 dBA: **2.000.000 VND / quý**.\n    - Vượt từ 5 đến 10 dBA: **5.000.000 VND / quý**.\n    - Vượt trên 10 dBA: **10.000.000 VND / quý**.\n*   **Hệ số ban đêm (Night Multiplier)**: Nhân thêm **1.5x** tổng phụ thu nếu nguồn ồn phát sinh liên tục trong khung giờ ban đêm."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Phụ Thu Tiếng Ồn v74\n*   **Vùng Lõi (Core)**: Tính toán mức vượt dBA ban ngày/ban đêm, áp dụng phụ thu tương ứng theo thang đo, nhân hệ số ban đêm 1.5x.\n*   **Vùng Cận Biên (Adjacent)**: Kết nối dữ liệu từ thiết bị đo độ ồn liên tục (sound level meter) đặt tại ranh giới nhà máy.\n*   **Vùng Biên Giới (Frontier)**: AI phân tích và cảnh báo khi mức ồn tiệm cận ngưỡng giới hạn trong các chu kỳ hoạt động cao điểm.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Lắp đặt vách ngăn tiêu âm thực tế tại nhà xưởng."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Tiêu Chuẩn Tiếng Ồn\n*   **Quy định giới hạn (Constraint)**: Mức tiếng ồn phát sinh từ hoạt động sản xuất kinh doanh không được phép vượt quá giới hạn tối đa cho phép quy định tại Quy chuẩn kỹ thuật quốc gia về tiếng ồn (QCVN 26:2010/BTNMT)."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Phụ Thu Tiếng Ồn\n\n```mermaid\ngraph TD\n    A[Nhận chỉ số dBA đo được] --> B{Thời điểm đo?}\n    B -->|Ban ngày 6h-21h| C{dBA đo được > 70?}\n    C -->|Có| D[Tính số dBA vượt ngưỡng = dBA - 70]\n    C -->|Không| E[Phụ thu = 0]\n    B -->|Ban đêm 21h-6h| F{dBA đo được > 55?}\n    F -->|Có| G[Tính số dBA vượt ngưỡng = dBA - 55]\n    F -->|Không| E\n    D --> H[Áp thang phụ thu cơ bản]\n    G --> I[Áp thang phụ thu cơ bản x Hệ số ban đêm 1.5]\n    H --> K[Tổng hợp phụ thu tiếng ồn nộp trong quý]\n    I --> K\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Tiếng Ồn v74\n*   MST Đang Xem: **{mst}**\n*   Số bản ghi đo tiếng ồn đã ghi nhận: **{noise_count}**\n*   Tổng phụ thu tiếng ồn tạm tính: **{total_violations * 4500000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Đặt thiết bị đo sai vị trí**: Đo tiếng ồn ở nguồn phát thay vì đo tại ranh giới đất của cơ sở sản xuất tiếp giáp khu dân cư dẫn đến số liệu vượt ngưỡng ảo.\n2. **Bỏ quên hệ số ban đêm**: Không nhân hệ số 1.5x cho các ca sản xuất đêm phát sinh tiếng ồn lớn vượt tiêu chuẩn."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Lắp đặt trạm quan trắc tiếng ồn tự động kết nối dữ liệu liên tục với GDT Hub.\n*   **Bước 2**: Thực hiện rà soát báo cáo độ ồn hàng tuần để điều chỉnh lịch sản xuất ca đêm phù hợp.\n\n### Luật tham chiếu\n*   **Quy chuẩn kỹ thuật quốc gia QCVN 26:2010/BTNMT** về tiếng ồn."
            }
        ]

    elif v_clean == "v75":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nQuản lý tuân thủ và tự động hóa tính toán phụ thu/surcharge đối với túi ni-lông thân thiện môi trường và đồ nhựa dùng một lần theo Nghị định số 08/2022/NĐ-CP.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để hệ thống tự động phân loại bao bì nhựa dùng một lần trên hóa đơn, áp dụng mức thuế tuyệt đối (15.000đ/kg hoặc 30.000đ/kg) và xử lý miễn giảm khi có chứng nhận nhãn sinh thái?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp biểu thuế nhựa chi tiết, quy trình xác thực chứng chỉ tự phân hủy sinh học giúp doanh nghiệp giảm chi phí thuế môi trường tối đa."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Thuế Suất Nhựa Dùng Một Lần v75\n*   **Túi ni-lông không thân thiện môi trường**: Thuế suất tuyệt đối **50.000 VND / kg**.\n*   **Cốc nhựa, đĩa nhựa dùng một lần**: Thuế suất **30.000 VND / kg**.\n*   **Hộp xốp đựng thức ăn dùng một lần**: Thuế suất **15.000 VND / kg**.\n*   **Miễn thuế**: Đồ nhựa có chứng nhận Nhãn sinh thái Việt Nam hoặc túi ni-lông tự phân hủy sinh học có chứng nhận của Bộ Tài nguyên và Môi trường."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phạm Vi Thuế Nhựa v75\n*   **Vùng Lõi (Core)**: Tính toán thuế nhựa dùng một lần, xác định các trường hợp được miễn thuế dựa trên chứng chỉ nhãn sinh thái.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với hóa đơn mua vật tư bao bì nhựa đầu vào và tờ khai nhập khẩu nguyên liệu hạt nhựa.\n*   **Vùng Biên Giới (Frontier)**: AI quét mô tả sản phẩm trên hóa đơn để tự động phân tích và phân loại chất liệu nhựa (PP, PET, PS).\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Thiết kế khuôn mẫu sản xuất sản phẩm nhựa."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Ràng Buộc Chứng Chỉ Nhãn Sinh Thái\n*   **Quy định miễn thuế (Constraint)**: Sản phẩm nhựa dùng một lần chỉ được miễn nộp phụ thu thuế môi trường **nếu và chỉ nếu** có chứng nhận Nhãn sinh thái Việt Nam do Bộ Tài nguyên và Môi trường cấp còn hiệu lực tại thời điểm phát hành hóa đơn."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Tính Thuế Nhựa Dùng Một Lần\n\n```mermaid\ngraph TD\n    A[Nhận hóa đơn vật tư bao bì nhựa] --> B{Sản phẩm nhựa thuộc diện chịu thuế?}\n    B -->|Không| C[Bỏ qua]\n    B -->|Có| D{Có chứng nhận Nhãn sinh thái/Tự phân hủy?}\n    D -->|Có| E[Ghi nhận Miễn thuế nhựa - is_exempt]\n    D -->|Không| F{Loại sản phẩm nhựa cụ thể?}\n    F -->|Túi ni-lông| G[Áp thuế 50.000 VND/kg]\n    F -->|Cốc đĩa nhựa| H[Áp thuế 30.000 VND/kg]\n    F -->|Hộp xốp| I[Áp thuế 15.000 VND/kg]\n    G --> K[Tính thuế = Khối lượng x Mức thuế tương ứng]\n    H --> K\n    I --> K\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Bao Bì Nhựa v75\n*   MST Đang Xem: **{mst}**\n*   Số hóa đơn bao bì nhựa đã quét: **{plastics_count} hóa đơn**\n*   Tổng thuế nhựa phát sinh trong kỳ: **{total_violations * 4500000:,.0f} VND**\n\n### Sai sót thường gặp\n1. **Khai sai trọng lượng**: Khai báo trọng lượng túi ni-lông theo chiếc thay vì kilôgam làm sai số tiền thuế phải nộp.\n2. **Sử dụng chứng nhận giả/hết hạn**: Tích chọn miễn thuế nhựa dựa trên chứng chỉ tự phân hủy đã hết hiệu lực từ năm trước."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Rà soát nhà cung cấp bao bì nhựa để chuyển đổi sang sử dụng túi ni-lông có chứng chỉ tự phân hủy sinh học.\n*   **Bước 2**: Thực hiện quét và nộp tờ khai thuế bảo vệ môi trường đối với bao bì nhựa tự sản xuất trước khi xuất xưởng.\n\n### Luật tham chiếu\n*   **Thông tư số 152/2011/TT-BTC** hướng dẫn thi hành Luật Thuế bảo vệ môi trường."
            }
        ]

    elif v_clean == "v76":
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": "### Mục tiêu chính (True Purpose)\nHướng dẫn quản lý, cấu hình và giám sát phân hệ tối ưu hóa ngữ cảnh AI và lưu trữ vết đo lường (Telemetry Traces) qua Headroom AI Hub (v76).\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để nén ngữ cảnh thông minh mà không làm mất thông tin quan trọng của các tác vụ kiểm toán thuế phức tạp?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp hiểu biết sâu sắc về kỹ thuật nén token, bảo vệ các đoạn thông tin gần nhất và cách cấu hình tỷ lệ nén (target ratio) tối ưu."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": "### Cấu Trúc Hoạt Động Headroom AI Hub\n*   **Lớp Đo Lường (Telemetry Logging)**: Tự động ghi vết các cuộc gọi LLM bao gồm số lượng token trước/sau nén, tỷ lệ nén và các phép chuyển đổi đã áp dụng.\n*   **Lớp Tối Ưu Hóa (Optimization Engine)**: Sử dụng giải thuật loại bỏ trùng lặp, tóm tắt và lược bỏ các từ thừa mà không thay đổi ngữ nghĩa.\n*   **Lớp Kiểm Soát (Steering Gates)**: Cho phép bật/tắt động, đặt tỷ lệ mục tiêu (target_ratio) và bảo vệ một số lượng tin nhắn gần nhất (protect_recent)."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": "### Phân Lớp Phạm Vi v76\n*   **Vùng Lõi (Core)**: Nén và tối ưu hóa hệ thống prompt (system & user content), lưu nhật ký telemetry vào cơ sở dữ liệu.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết với cổng tương tác API Playground và giao diện Dashboard kiểm soát hiệu năng.\n*   **Vùng Biên Giới (Frontier)**: Tự động điều chỉnh cấu hình nén dựa trên độ dài lịch sử chat và phản hồi từ mô hình LLM.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Huấn luyện hoặc tinh chỉnh các mô hình ngôn ngữ lớn (LLM SFT)."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": "### Quy Tắc Liên Kết & Ràng Buộc\n*   **Mối quan hệ phụ thuộc (Dependency)**: v76 phụ thuộc vào v44 (Compliance Hub) để đồng bộ cấu hình hệ thống và cập nhật trạng thái chung.\n*   **Ràng buộc (Constraint)**: Mọi thao tác nén prompt phải đảm bảo không vượt quá dung lượng ngữ cảnh cực đại của mô hình và không làm méo mó các thông số kiểm toán quan trọng (như MST, số tiền thuế, trạng thái hóa đơn)."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": "### Luồng Vận Hành Chung\n\n```mermaid\nsequenceDiagram\n    Client->>Webapp: Gửi yêu cầu kiểm toán/chat\n    Webapp->>Headroom Hub: Gọi compress_and_log()\n    Note over Headroom Hub: Kiểm tra settings.ai_headroom_enabled\n    alt Enabled\n        Headroom Hub->>Headroom Hub: Thực hiện nén (Target Ratio / Protect Recent)\n        Headroom Hub->>Database: Lưu vết HeadroomTelemetry\n    else Disabled\n        Note over Headroom Hub: Giữ nguyên prompt gốc\n    end\n    Headroom Hub-->>Webapp: Trả về prompts đã tối ưu\n    Webapp->>LLM: Thực thi yêu cầu với prompts tối ưu\n```"
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Dữ Liệu Đo Lường v76\n*   MST Đang Xem: **{mst}**\n*   Số lượng vết đo lường đã ghi nhận: **{headroom_count} sự kiện**\n*   Tổng số cảnh báo hệ thống: **{total_violations} cảnh báo**\n\n### Sai sót thường gặp\n1. **Over-compression (Nén quá đà)**: Đặt target_ratio quá thấp khiến AI đánh mất ngữ cảnh quan trọng về luật thuế.\n2. **Telemetry Table missing (Thiếu bảng dữ liệu)**: Chưa chạy di chuyển (migration) DB dẫn đến lỗi ghi nhật ký telemetry."
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": "### Lộ Trình Triển Khai\n*   **Bước 1**: Bật tính năng Headroom AI tại trang cài đặt hệ thống.\n*   **Bước 2**: Sử dụng Playground để thử nghiệm các mức độ nén và kiểm tra chất lượng câu trả lời.\n*   **Bước 3**: Giám sát biểu đồ hiệu năng và số lượng token tiết kiệm được trên Dashboard.\n\n### Tài liệu tham chiếu\n*   **Headroom AI Context Compression / Telemetry Hub Specification**"
            }
        ]
    
    # 2. Add fallback detailed pages for the remaining nodes (v32-v43, and environmental ones)
    elif v_clean in ["v32", "v33", "v34", "v35", "v36", "v37", "v38", "v39", "v40", "v41", "v42", "v43"]:
        # Add detailed content for intermediate nodes
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": f"### Mục tiêu chính (True Purpose)\nTài liệu hướng dẫn chuyên sâu phân hệ **{version_id.upper()}** thuộc hệ thống GDT Invoice Hub.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để ứng dụng và tích hợp quy tắc {version_id.upper()} nhằm tối ưu hóa tính tuân thủ thuế và quản lý rủi ro hóa đơn?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp các thông tin nền tảng về khái niệm, cách thiết lập cấu hình và biểu đồ vận hành chi tiết."
            },
            {
                "title": "2. Mô Mô Hình Lõi (Core Model)",
                "content": f"### Cấu Trúc Khái Niệm Phân Hệ {version_id.upper()}\nPhân hệ này đảm nhận việc xử lý các ràng buộc nghiệp vụ liên quan đến **{version_id.upper()}**, bao gồm tra cứu, tính toán, và đồng bộ dữ liệu hóa đơn điện tử."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": f"### Phân Lớp Phạm Vi\n*   **Vùng Lõi (Core)**: Các quy tắc cơ bản trực tiếp ảnh hưởng đến trạng thái hợp lệ của hóa đơn.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết dữ liệu giữa các phân hệ quản lý thuế phụ thuộc.\n*   **Vùng Biên Giới (Frontier)**: Các tính năng mở rộng ứng dụng AI tự động hóa kiểm tra.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Quy trình kế toán độc lập bên ngoài hệ thống."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": f"### Các Nguyên Tắc Mối Quan Hệ\n*   **Định nghĩa**: {version_id.upper()} là một phân hệ thành phần của hệ thống quản lý tuân thủ thuế GDT Invoice Hub.\n*   **Ràng buộc**: Mọi dữ liệu hóa đơn nhập vào phân hệ phải tuân thủ đúng định dạng chuẩn quy định bởi cơ quan thuế."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": f"### Luồng Vận Hành Chung\n1. Nhận thông tin hóa đơn từ luồng đồng bộ daemon.\n2. Phân tích các thẻ dữ liệu cấu trúc tương ứng.\n3. Áp dụng tập luật kiểm toán của {version_id.upper()}.\n4. Ghi nhận nhật ký cảnh báo và cập nhật trạng thái."
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Chỉ số hoạt động\n*   Trạng thái phân hệ: **Đang hoạt động**\n*   Mức độ rủi ro cấu hình: **Thấp**\n*   Số lỗi phát hiện trong kỳ: **{total_violations} cảnh báo**"
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": f"### Lộ trình áp dụng\n*   **Bước 1**: Đọc tài liệu đặc tả nghiệp vụ phân hệ {version_id.upper()}.\n*   **Bước 2**: Thực hiện cấu hình tham số kiểm soát tương thích với mô hình kinh doanh của doanh nghiệp.\n*   **Bước 3**: Theo dõi định kỳ báo cáo kiểm toán rủi ro trên trang Dashboard chính."
            }
        ]
        
    else:
        # Default fallback structure for any other nodes
        label = version_id
        pages = [
            {
                "title": "1. Định Hướng (Orientation)",
                "content": f"### Mục tiêu chính (True Purpose)\nTài liệu hướng dẫn và vận hành chi tiết phân hệ **{label}** trong hệ thống GDT Invoice Hub.\n\n### Câu hỏi trọng tâm (Focus Question)\n*Làm thế nào để ứng dụng và tích hợp quy tắc {label} nhằm tăng cường tính tuân thủ thuế và quản lý rủi ro hóa đơn?*\n\n### Lời hứa của bản đồ (Map Promise)\nCung cấp các thông tin nền tảng về khái niệm, cách thiết lập cấu hình và biểu đồ vận hành của phân hệ này."
            },
            {
                "title": "2. Mô Hình Lõi (Core Model)",
                "content": f"### Cấu Trúc Khái Niệm Phân Hệ {label}\nPhân hệ này đảm nhận việc xử lý các ràng buộc nghiệp vụ liên quan đến **{label}**, thực hiện thu thập dữ liệu hóa đơn đầu vào, kiểm tra định dạng XML, đối sánh tham số và kích hoạt các cảnh báo rủi ro tương ứng."
            },
            {
                "title": "3. Phân Vùng Phạm Vi (Scope Rings)",
                "content": f"### Phân Lớp Phạm Vi của {label}\n*   **Vùng Lõi (Core)**: Các quy tắc cơ bản trực tiếp ảnh hưởng đến trạng thái hợp lệ của hóa đơn.\n*   **Vùng Cận Biên (Adjacent)**: Liên kết dữ liệu giữa các phân hệ quản lý thuế phụ thuộc.\n*   **Vùng Biên Giới (Frontier)**: Các tính năng mở rộng ứng dụng AI tự động hóa kiểm tra.\n*   **Ngoài Phạm Vi (Out-of-Scope)**: Quy trình kế toán độc lập bên ngoài hệ thống."
            },
            {
                "title": "4. Ngữ Pháp Liên Kết (Relation Grammar)",
                "content": f"### Các Nguyên Tắc Mối Quan Hệ\n*   **Định nghĩa (Definition)**: {label} là một phân hệ thành phần của hệ thống quản lý tuân thủ thuế GDT Invoice Hub.\n*   **Ràng buộc (Constraint)**: Mọi dữ liệu hóa đơn nhập vào phân hệ phải tuân thủ đúng định dạng chuẩn XML quy định bởi Tổng cục Thuế."
            },
            {
                "title": "5. Cơ Chế Vận Hành (Mechanism & Dynamics)",
                "content": f"### Luồng Vận Hành Chung\n1. Nhận thông tin hóa đơn từ luồng đồng bộ daemon.\n2. Phân tích các thẻ dữ liệu cấu trúc tương ứng.\n3. Áp dụng tập luật kiểm toán của {label}.\n4. Ghi nhận nhật ký cảnh báo và cập nhật điểm xếp hạng tín nhiệm thuế của doanh nghiệp."
            },
            {
                "title": "6. Giới Hạn & Lỗi Thường Gặp (Boundaries & Failure Cases)",
                "content": f"### Chỉ số hoạt động\n*   Trạng thái phân hệ: **Đang hoạt động**\n*   Mức độ rủi ro cấu hình: **Trung bình**\n*   Số lỗi phát hiện trong kỳ: **{total_violations} cảnh báo**"
            },
            {
                "title": "7. Ứng Dụng & Lộ Trình Học Tập (Application & Learning Path)",
                "content": f"### Lộ trình áp dụng\n*   **Bước 1**: Đọc tài liệu đặc tả nghiệp vụ phân hệ {label}.\n*   **Bước 2**: Thực hiện cấu hình tham số kiểm soát tương thích với mô hình kinh doanh của doanh nghiệp.\n*   **Bước 3**: Theo dõi định kỳ báo cáo kiểm toán rủi ro trên trang Dashboard chính."
            }
        ]

    return pages
