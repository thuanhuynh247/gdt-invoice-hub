import fitz
import os

def create_pdf(filename, title, sections):
    doc = fitz.open()
    
    # Page dimensions (Letter / A4 size is roughly 595 x 842 pt)
    width, height = 595, 842
    margin = 50
    rect = fitz.Rect(margin, margin + 60, width - margin, height - margin)
    
    # Font path for Windows Arial to support Vietnamese Unicode
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if not os.path.exists(font_path):
        font_path = None # Fallback to standard Helvetica if Windows Arial is missing
    
    # Title Page / First Page
    page = doc.new_page(width=width, height=height)
    
    # Draw header block
    page.insert_textbox(
        fitz.Rect(margin, margin, width - margin, margin + 50),
        f"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n---------\n{title.upper()}",
        fontsize=12,
        fontname="arial" if font_path else "helv",
        fontfile=font_path,
        align=fitz.TEXT_ALIGN_CENTER
    )
    
    current_text = ""
    for sec_title, sec_content in sections:
        current_text += f"\n\n--- {sec_title} ---\n{sec_content}\n"
    
    # Split text into pages based on insert_textbox returning -1 or remaining text length
    words = current_text.split()
    chunks = []
    current_chunk = []
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= 150:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    for idx, chunk in enumerate(chunks):
        if idx == 0:
            p = page
        else:
            p = doc.new_page(width=width, height=height)
        
        # Draw header on subsequent pages
        if idx > 0:
            p.insert_textbox(
                fitz.Rect(margin, margin, width - margin, margin + 30),
                f"{title} - Trang {idx + 1}",
                fontsize=9,
                fontname="arial" if font_path else "helv",
                fontfile=font_path,
                align=fitz.TEXT_ALIGN_RIGHT
            )
            
        p.insert_textbox(
            rect,
            chunk,
            fontsize=10.5,
            fontname="arial" if font_path else "helv",
            fontfile=font_path,
            align=fitz.TEXT_ALIGN_LEFT
        )
        
    doc.save(filename)
    doc.close()
    print(f"Successfully generated {filename} with {len(chunks)} pages.")

# 1. Nghị định 252/2026/NĐ-CP
sections_nd252 = [
    ("ĐIỀU 1. PHẠM VI ĐIỀU CHỈNH VÀ HIỆU LỰC THI HÀNH", 
     "Nghị định số 252/2026/NĐ-CP về kê khai thuế và hoàn thuế có hiệu lực từ ngày 01/07/2026. Nghị định này thay thế các Nghị định trước đây: Nghị định số 373/2025/NĐ-CP (quy định và biểu mẫu về kê khai quyết toán thuế), Nghị định số 117/2025/NĐ-CP (chủ sàn TMĐT chịu trách nhiệm nộp thay thuế cho các shop online), Nghị định số 49/2025/NĐ-CP (ngưỡng nợ thuế bị tạm hoãn xuất cảnh áp dụng từ 28/2/2025), Nghị định số 91/2022/NĐ-CP (quy định hạn mức tạm nộp thuế TNDN), và Nghị định số 126/2020/NĐ-CP (quy định chung về quản lý thuế)."),
    
    ("ĐIỀU 2. QUY ĐỊNH MỚI VỀ CHẾ ĐỘ ƯU TIÊN VÀ APA", 
     "Quy định cụ thể và đơn giản hóa chế độ ưu tiên đối với người nộp thuế có giao dịch liên kết, bao gồm việc ưu tiên xử lý hồ sơ thỏa thuận trước về phương pháp xác định giá tính thuế (APA). Gỡ bỏ hoàn toàn quy định về doanh nghiệp ưu tiên trong lĩnh vực hải quan trong nghị định này. Gỡ bỏ cơ chế ủy nhiệm thu thuế trước đây."),
    
    ("ĐIỀU 3. HẠN MỨC TẠM NỘP THUẾ TNDN VÀ XUẤT CẢNH", 
     "Tổng số thuế TNDN hoặc lợi nhuận sau thuế đã tạm nộp của 4 quý không được thấp hơn 80% số phải nộp theo quyết toán năm (thay đổi so với mức 80% của 3 quý đầu năm ở Nghị định 91/2022/NĐ-CP). Đảm bảo ngưỡng tạm nộp thuế TNDN hàng quý đạt từ 80% trở lên cho cả 4 quý để tránh bị phạt tiền chậm nộp thuế 0.03% mỗi ngày. Trình tự, thủ tục thông báo tạm hoãn xuất cảnh do nợ thuế được quy định rõ ràng, chi tiết hơn để tránh lạm dụng, bảo đảm quyền lợi người nộp thuế."),
    
    ("ĐIỀU 4. QUẢN LÝ THUẾ THƯƠNG MẠI ĐIỆN TỬ", 
     "Chủ sàn thương mại điện tử chịu trách nhiệm khai nộp thay, khấu trừ thuế trực tiếp cho các shop online kinh doanh trên sàn. Thời hạn thông báo tạm ngừng kinh doanh và thời hạn thay đổi thông tin đăng ký thuế của cá nhân được điều chỉnh linh hoạt hơn."),
    
    ("ĐIỀU 5. KHAI BỔ SUNG VÀ CHUYỂN ĐỔI LOẠI HÌNH DOANH NGHIỆP", 
     "Hướng dẫn chi tiết khai bổ sung hồ sơ khai thuế khi thay đổi kỳ tính thuế từ quý sang tháng. Quy định trách nhiệm pháp lý của doanh nghiệp kế thừa và các mốc thời gian chốt số liệu cụ thể khi chuyển đổi loại hình doanh nghiệp. Đảm bảo thời hạn nộp hồ sơ khai thuế và giới hạn nghiêm ngặt về thời gian cũng như trường hợp được khai bổ sung hồ sơ thuế.")
]

# 2. Nghị định 253/2026/NĐ-CP
sections_nd253 = [
    ("ĐIỀU 1. PHẠM VI ĐIỀU CHỈNH VÀ HIỆU LỰC THI HÀNH", 
     "Nghị định số 253/2026/NĐ-CP về kê khai và tính thuế Thu nhập cá nhân (TNCN) có hiệu lực từ ngày 01/07/2026. Nghị định này thay thế Nghị định số 65/2013/NĐ-CP (quy định chi tiết Luật Thuế TNCN từ 1/7/2013)."),
    
    ("ĐIỀU 2. TIÊU CHÍ CÁ NHÂN CƯ TRÚ VÀ THU NHẬP CHỊU THUẾ", 
     "Tiêu chí xác định cá nhân cư trú được cập nhật rõ ràng hơn dựa trên số ngày có mặt thực tế và nơi ở thường trú hoặc thuê nhà tại Việt Nam. Quy định chi tiết các khoản thu nhập chịu thuế từ tiền lương, tiền công, bao gồm các khoản lợi ích bằng tiền hoặc không bằng tiền do người sử dụng lao động trả thay. Cập nhật quy định giảm trừ gia cảnh cho bản thân người nộp thuế và người phụ thuộc. Điều kiện đăng ký và hồ sơ chứng minh người phụ thuộc được đơn giản hóa. Ngưỡng thu nhập vãng lai không phải quyết toán thuế và ngưỡng khấu trừ 10% đối với thu nhập vãng lai hoặc ngắn hạn được điều chỉnh tăng lên nhằm giảm thiểu thủ tục hành chính cho người lao động có thu nhập thấp."),
    
    ("ĐIỀU 3. CẬP NHẬT THUẾ SUẤT CHUYỂN NHƯỢNG VÀ GÓP VỐN", 
     "Thuế suất đối với chuyển nhượng vốn (không phải chứng khoán): Áp dụng mức thuế suất 20% trên thu nhập tính thuế. Thuế suất chuyển nhượng chứng khoán: Áp dụng thống nhất thuế suất 0.1% trên giá chuyển nhượng chứng khoán mỗi lần giao dịch. Thuế suất chuyển nhượng bất động sản: Áp dụng thuế suất thống nhất 2% trên giá chuyển nhượng bất động sản. Xử lý thuế khi cá nhân góp vốn bằng tài sản vào doanh nghiệp: Thời điểm tính thuế và ghi nhận thu nhập từ chuyển nhượng vốn được hoãn cho đến khi cá nhân thực tế chuyển nhượng phần vốn góp đó. Kỳ tính thuế đối với người nước ngoài là cá nhân cư trú được tính theo năm dương lịch hoặc 12 tháng liên tục kể từ ngày đầu tiên có mặt tại Việt Nam."),
    
    ("ĐIỀU 4. GỠ BỎ PHƯƠNG PHÁP TÍNH THUẾ CŨ", 
     "Gỡ bỏ phương pháp tính thuế 25% trên thu nhập tính thuế đối với chuyển nhượng bất động sản (chỉ còn áp dụng duy nhất phương pháp thuế suất 2% trên giá bán). Gỡ bỏ phương pháp tính thuế 20% trên thu nhập tính thuế đối với chuyển nhượng chứng khoán (chỉ còn áp dụng duy nhất thuế suất 0.1% trên giá bán). Gỡ bỏ quy định trực tiếp về việc cơ quan thuế ấn định tỷ lệ thu nhập chịu thuế đối với cá nhân kinh doanh không thực hiện đúng chế độ kế toán, hóa đơn, chứng từ."),
    
    ("ĐIỀU 5. KHOẢN GIẢM TRỪ VÀ MIỄN THUẾ TNCN MỚI", 
     "Khoán chi văn phòng phẩm, công tác phí, điện thoại, trang phục được trừ theo quy chế của doanh nghiệp nhưng không vượt quá định mức quy định. Tiền ăn giữa ca, ăn trưa không vượt quá mức quy định. Tiền thuê nhà, dịch vụ kèm theo do người sử dụng lao động trả thay được tính vào thu nhập chịu thuế nhưng không vượt quá 15% tổng thu nhập chịu thuế (chưa bao gồm tiền thuê nhà). Bổ sung quy định mới về giảm trừ chi phí y tế và giáo dục - đào tạo thực tế có chứng từ hợp pháp cho bản thân người nộp thuế, với tổng mức giảm trừ mới tối đa cho y tế và giáo dục được nâng lên đáng kể. Quy định cụ thể thời điểm tính thuế TNCN đối với cổ phiếu thưởng và quyền mua cổ phiếu là thời điểm bán/chuyển nhượng.")
]

# 3. Nghị định 254/2026/NĐ-CP
sections_nd254 = [
    ("ĐIỀU 1. PHẠM VI ĐIỀU CHỈNH VÀ HIỆU LỰC THI HÀNH", 
     "Nghị định số 254/2026/NĐ-CP về hóa đơn điện tử và chứng từ điện tử có hiệu lực từ ngày 01/07/2026. Nghị định này thay thế Nghị định số 123/2020/NĐ-CP và Nghị định số 70/2025/NĐ-CP."),
    
    ("ĐIỀU 2. TRÁCH NHIỆM LẬP HÓA ĐƠN VÀ TMĐT", 
     "Người bán có quyền yêu cầu sàn thương mại điện tử cung cấp dữ liệu định danh, thông tin giao dịch của người mua để phục vụ việc lập hóa đơn điện tử chính xác. Quy định rõ ràng trách nhiệm của bên ủy nhiệm và bên nhận ủy nhiệm lập hóa đơn điện tử, tránh tranh chấp pháp lý về thời điểm lập và chịu trách nhiệm nội dung hóa đơn. Cơ chế khen thưởng đối với người tiêu dùng tố giác hành vi của doanh nghiệp hoặc hộ kinh doanh không xuất hóa đơn điện tử khi bán hàng hóa, dịch vụ."),
    
    ("ĐIỀU 3. HÀNH VI SỬ DỤNG HÓA ĐƠN KHÔNG HỢP PHÁP", 
     "Định nghĩa rõ ràng và hình thức xử lý nghiêm khắc đối với hành vi sử dụng 'hóa đơn, chứng từ giả' hoặc 'sử dụng hóa đơn, chứng từ không hợp pháp' và 'sử dụng không hợp pháp hóa đơn'. Nghiêm cấm lạm dụng dữ liệu hóa đơn được ủy nhiệm cho các mục đích thương mại ngoài phạm vi thỏa thuận. Quy định thời hạn cuối cùng sử dụng biên lai giấy tự in, đặt in và xử lý chuyển tiếp biên lai thuế. Hóa đơn đặt in của cơ quan thuế hết hoàn toàn giá trị sử dụng."),
    
    ("ĐIỀU 4. BẢN GIẤY CHUYỂN ĐỔI VÀ HÓA ĐƠN TỪ MÁY TÍNH TIỀN", 
     "Giới hạn hiệu lực của bản giấy chuyển đổi từ hóa đơn điện tử: Bản giấy chuyển đổi chỉ có giá trị lưu giữ, đối chiếu thông tin chứ không có giá trị thanh toán hay dùng để kê khai khấu trừ thuế. Giải thích rõ định nghĩa 'hóa đơn điện tử khởi tạo từ máy tính tiền' có kết nối chuyển dữ liệu điện tử với cơ quan thuế. Đối tượng được sử dụng hóa đơn điện tử không có mã của cơ quan thuế được thu hẹp lại, ưu tiên chuyển sang sử dụng hóa đơn có mã để kiểm soát dòng tiền tốt hơn."),
    
    ("ĐIỀU 5. BẮT BUỘC XUẤT HÓA ĐƠN CHO TỪNG LẦN BÁN", 
     "Bắt buộc lập hóa đơn điện tử cho từng lần bán hàng đối với người mua lẻ (không được gộp chung doanh thu cuối ngày đối với các ngành hàng ăn uống, bán lẻ, xăng dầu). Thời điểm lập hóa đơn điện tử đối với xuất khẩu hàng hóa là thời điểm hoàn thành thủ tục hải quan và chuyển giao quyền sở hữu hàng hóa. Thời điểm lập hóa đơn đối với hoạt động casino, kinh doanh trò chơi điện tử có thưởng.")
]

# 4. Nghị định 255/2026/NĐ-CP
sections_nd255 = [
    ("ĐIỀU 1. PHẠM VI ĐIỀU CHỈNH VÀ HIỆU LỰC THI HÀNH", 
     "Nghị định số 255/2026/NĐ-CP về quản lý thuế đối với doanh nghiệp có giao dịch liên kết (GDLK) có hiệu lực từ ngày 01/07/2026. Nghị định này thay thế Nghị định số 132/2020/NĐ-CP và Nghị định số 20/2025/NĐ-CP."),
    
    ("ĐIỀU 2. QUAN HỆ LIÊN KẾT VÀ CƠ SỞ DỮ LIỆU", 
     "Gỡ bỏ định nghĩa 'Cơ sở dữ liệu của Cơ quan thuế' nhằm tăng tính minh bạch và khuyến khích doanh nghiệp sử dụng các nguồn dữ liệu độc lập, khách quan để so sánh giá. Định nghĩa rõ ràng hơn về 'Giao dịch liên kết' và 'Cơ sở dữ liệu thương mại' được công nhận để phục vụ mục đích so sánh giá độc lập."),
    
    ("ĐIỀU 3. XÁC ĐỊNH QUAN HỆ LIÊN KẾT QUA KHOẢN VAY", 
     "Làm rõ các căn cứ để xác định hai doanh nghiệp có quan hệ liên kết. Khoản vay vốn từ ngân hàng thương mại độc lập sẽ không còn bị xem là có giao dịch liên kết nếu không thuộc trường hợp chỉ định điều hành hoặc chiếm tỷ lệ chi phối vốn."),
    
    ("ĐIỀU 4. BÁO CÁO LỢI NHUẬN LIÊN QUỐC GIA (CbCR)", 
     "Điều chỉnh ngưỡng doanh thu để nộp Báo cáo lợi nhuận liên quốc gia (CbCR) phù hợp với chuẩn mực quốc tế BEPS của OECD. Ngưỡng doanh thu miễn lập Hồ sơ xác định giá giao dịch liên kết (áp dụng chức năng đơn giản hóa) giúp doanh nghiệp quy mô nhỏ giảm chi phí tuân thủ. Nghĩa vụ kê khai của người nộp thuế và trách nhiệm của Ngân hàng Nhà nước trong việc chia sẻ thông tin dòng tiền liên quốc gia để chống chuyển giá."),
    
    ("ĐIỀU 5. TRẦN CHI PHÍ LÃI VAY EBITDA 30%", 
     "Nguyên tắc cốt lõi: Điều chỉnh giá giao dịch liên kết không được làm giảm nghĩa vụ thuế TNDN phải nộp tại Việt Nam. Giới hạn chi phí lãi vay được trừ khi tính thuế TNDN (trần EBITDA): Chi phí lãi vay ròng sau khi trừ lãi tiền gửi và lãi cho vay được trừ không vượt quá 30% của tổng chỉ số EBITDA của doanh nghiệp trong kỳ tính thuế. Kê khai thuế phải dựa trên bản chất giao dịch thực tế thay vì hình thức pháp lý. Cung cấp hồ sơ trong 15 ngày làm việc khi thanh tra.")
]

# Write the PDFs to workspace root
create_pdf("nghidinh252_2026.pdf", "Nghị định 252/2026/NĐ-CP", sections_nd252)
create_pdf("nghidinh253_2026.pdf", "Nghị định 253/2026/NĐ-CP", sections_nd253)
create_pdf("nghidinh254_2026.pdf", "Nghị định 254/2026/NĐ-CP", sections_nd254)
create_pdf("nghidinh255_2026.pdf", "Nghị định 255/2026/NĐ-CP", sections_nd255)
