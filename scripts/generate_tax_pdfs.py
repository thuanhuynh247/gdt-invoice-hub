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
    
    # Draw a nice header block
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

# 1. Thông tư 69/2025/TT-BTC
sections_tt69 = [
    ("ĐIỀU 1. PHẠM VI ÁP DỤNG VÀ HIỆU LỰC THI HÀNH", 
     "Thông tư này có hiệu lực thi hành từ ngày 01 tháng 07 năm 2025. Thông tư này quy định chi tiết một số điều của Luật Thuế giá trị gia tăng (GTGT) 2024 và hướng dẫn thực hiện Nghị định số 181/2025/NĐ-CP của Chính phủ. Văn bản này thay thế hoàn toàn cho Thông tư số 219/2013/TT-BTC và các thông tư sửa đổi bổ sung liên quan trước đây."),
    
    ("ĐIỀU 2. QUY ĐỊNH HẠN MỨC THANH TOÁN KHÔNG DÙNG TIỀN MẶT", 
     "Thực hiện Luật số 48/2024/QH15, ngưỡng thanh toán không dùng tiền mặt bắt buộc đối với việc khấu trừ thuế GTGT đầu vào được điều chỉnh giảm từ 20 triệu đồng xuống còn 5 triệu đồng. Hóa đơn mua vào có giá trị thanh toán từ 5 triệu đồng trở lên bắt buộc phải có chứng từ thanh toán không dùng tiền mặt, cụ thể là chuyển khoản từ tài khoản ngân hàng của bên mua sang tài khoản ngân hàng của bên bán để được đủ điều kiện khấu trừ thuế GTGT và tính vào chi phí hợp lý khi xác định thuế TNDN. Quy định này nhằm tăng cường tính minh bạch giao dịch và hạn chế gian lận thương mại."),
    
    ("ĐIỀU 3. HỒ SƠ VÀ THỦ TỤC ÁP DỤNG THUẾ SUẤT 0% CHO XUẤT KHẨU", 
     "Đối với hàng hóa xuất khẩu, hồ sơ bao gồm: Tờ khai hải quan đã hoàn thành thủ tục hải quan, hợp đồng xuất khẩu ký với tổ chức nước ngoài, hóa đơn thương mại, và chứng từ thanh toán không dùng tiền mặt qua ngân hàng. Đối với dịch vụ xuất khẩu cung cấp cho tổ chức, cá nhân nước ngoài tiêu dùng ngoài lãnh thổ Việt Nam, hồ sơ bắt buộc phải có hợp đồng cung ứng dịch vụ, hóa đơn dịch vụ và chứng từ thanh toán qua ngân hàng thể hiện dòng tiền từ nước ngoài chảy vào Việt Nam. Các trường hợp không đáp ứng đầy đủ hồ sơ sẽ không được áp dụng mức thuế suất 0% mà phải tính theo mức thuế suất tương ứng của sản phẩm tiêu dùng nội địa."),
    
    ("ĐIỀU 4. KHẤU TRỪ VÀ HOÀN THUẾ GTGT CHO NHÀ THẦU NƯỚC NGOÀI", 
     "Tổ chức, cá nhân nước ngoài kinh doanh tại Việt Nam hoặc có thu nhập phát sinh tại Việt Nam không thành lập pháp nhân sẽ thực hiện nghĩa vụ thuế GTGT thông qua hình thức khấu trừ tại nguồn. Bên Việt Nam ký hợp đồng mua dịch vụ của nhà thầu nước ngoài có trách nhiệm khấu trừ, kê khai và nộp thay thuế GTGT cho nhà thầu nước ngoài theo tỷ lệ phần trăm quy định trên doanh thu trước khi thanh toán tiền cho nhà thầu nước ngoài."),
    
    ("ĐIỀU 5. PHƯƠNG PHÁP TÍNH THUẾ TRỰC TIẾP TRÊN DOANH THU", 
     "Các cơ sở kinh doanh, doanh nghiệp có doanh thu hàng năm dưới ngưỡng quy định hoặc không thực hiện đầy đủ chế độ kế toán hóa đơn chứng từ sẽ áp dụng phương pháp tính thuế GTGT trực tiếp. Tỷ lệ % tính thuế GTGT trên doanh thu được quy định cụ thể như sau: Hoạt động phân phối, cung cấp hàng hóa là 1%; Hoạt động dịch vụ, xây dựng không bao thầu nguyên vật liệu là 5%; Hoạt động sản xuất, vận tải, dịch vụ có gắn với hàng hóa, xây dựng có bao thầu nguyên vật liệu là 3%; Hoạt động kinh doanh khác là 2%.")
]

# 2. Thông tư 18/2026/TT-BTC
sections_tt18 = [
    ("ĐIỀU 1. PHẠM VI HƯỚNG DẪN QUẢN LÝ THUẾ HỘ KINH DOANH", 
     "Thông tư này ban hành ngày 05 tháng 03 năm 2026 và có hiệu lực thi hành từ ngày 12 tháng 03 năm 2026. Hướng dẫn chi tiết về hồ sơ khai thuế, nộp thuế, hoàn thuế và phương pháp quản lý thuế đối với hộ kinh doanh, cá nhân kinh doanh trên toàn quốc theo tinh thần cải cách hành chính và chuyển đổi số ngành thuế."),
    
    ("ĐIỀU 2. NÂNG NGƯỠNG MIỄN THUẾ LÊN 500 TRIỆU ĐỒNG/NĂM", 
     "Theo Luật số 149/2025/QH15 áp dụng từ năm 2026, ngưỡng doanh thu được miễn thuế GTGT và thuế TNCN đối với hộ kinh doanh, cá nhân kinh doanh chính thức được nâng lên mức 500 triệu đồng/năm. Hộ kinh doanh có doanh thu từ hoạt động sản xuất kinh doanh trong năm dương lịch từ 500 triệu đồng trở xuống không phải nộp thuế GTGT và không phải nộp thuế TNCN. Quy định này thay thế cho hạn mức cũ (100 triệu đồng và đề xuất 200 triệu đồng trước đây) nhằm giảm bớt gánh nặng thuế cho các hộ kinh doanh quy mô nhỏ, thúc đẩy kinh tế tự doanh phát triển."),
    
    ("ĐIỀU 3. PHƯƠNG PHÁP KÊ KHAI VÀ PHƯƠNG PHÁP KHOÁN", 
     "Hộ kinh doanh quy mô lớn đáp ứng tiêu chí về doanh thu hoặc lao động bắt buộc phải thực hiện nộp thuế theo phương pháp kê khai, thực hiện chế độ kế toán đơn giản và sử dụng hóa đơn điện tử có mã của cơ quan thuế. Đối với hộ kinh doanh quy mô nhỏ không thực hiện chế độ kế toán sẽ áp dụng phương pháp khoán doanh thu. Cơ quan thuế xác định mức doanh thu khoán và mức thuế khoán định kỳ hàng năm dựa trên cơ sở dữ liệu quốc gia và điều tra thực tế địa bàn."),
    
    ("ĐIỀU 4. BIỂU MẪU TỜ KHAI THUẾ MỚI CHO CÁ NHÂN KINH DOANH", 
     "Ban hành và hướng dẫn sử dụng Mẫu tờ khai thuế đối với hộ kinh doanh, cá nhân kinh doanh (Mẫu số 01/CNKD). Đối với tổ chức, cá nhân khai thuế thay, nộp thuế thay cho cá nhân kinh doanh sử dụng Mẫu số 01/TKN-CNKD. Các biểu mẫu này tích hợp mã QR và được thiết kế tối ưu để người nộp thuế thực hiện trực tuyến thông qua ứng dụng eTax Mobile hoặc cổng thông tin điện tử của Tổng cục Thuế."),
    
    ("ĐIỀU 5. THỦ TỤC HOÀN THUẾ GTGT NỘP THỪA", 
     "Trường hợp hộ kinh doanh nộp thừa tiền thuế GTGT, thuế TNCN do thay đổi phương pháp tính thuế hoặc ngừng hoạt động kinh doanh giữa chừng, hồ sơ hoàn thuế nộp thừa được xử lý tự động trong vòng 6 ngày làm việc kể từ ngày nhận đủ hồ sơ trực tuyến hợp lệ. Cơ quan thuế thực hiện hoàn trả tiền thuế nộp thừa vào tài khoản ngân hàng chính chủ của hộ kinh doanh đã đăng ký với cơ quan thuế.")
]

# 3. Nghị định 144/2026/NĐ-CP
sections_nd144 = [
    ("ĐIỀU 1. PHẠM VI SỬA ĐỔI NGHỊ ĐỊNH 181/2025/NĐ-CP", 
     "Nghị định này ban hành và có hiệu lực thi hành từ ngày 20 tháng 06 năm 2026. Sửa đổi, bổ dung một số điều của Nghị định số 181/2025/NĐ-CP quy định chi tiết thi hành Luật Thuế GTGT 2024 để giải quyết kịp thời các vướng mắc phát sinh trong thực tế triển khai."),
    
    ("ĐIỀU 2. BỔ SUNG CÁC DỊCH VỤ BẢO HIỂM KHÔNG CHỊU THUẾ GTGT", 
     "Nhằm bảo vệ quyền lợi an sinh xã hội và hỗ trợ phát triển kinh tế nông - thủy sản, Nghị định quy định các nhóm dịch vụ bảo hiểm sau đây thuộc đối tượng không chịu thuế GTGT bao gồm: Bảo hiểm nhân thọ, bảo hiểm sức khỏe, bảo hiểm học đường, bảo hiểm tai nạn con người; Bảo hiểm nông nghiệp bao gồm bảo hiểm vật nuôi, cây trồng; Bảo hiểm tàu, thuyền, trang thiết bị và dụng cụ trực tiếp phục vụ hoạt động đánh bắt thủy hải sản của ngư dân. Doanh thu từ hoạt động tái bảo hiểm và hoa hồng môi giới các loại bảo hiểm nêu trên cũng được miễn chịu thuế GTGT."),
    
    ("ĐIỀU 3. CHÍNH SÁCH THUẾ GTGT ĐỐI VỚI KHOÁNG SẢN XUẤT KHẨU", 
     "Các sản phẩm tài nguyên, khoáng sản xuất khẩu thô hoặc chưa chế biến thành sản phẩm khác thuộc đối tượng không chịu thuế GTGT (thuế suất đầu ra không chịu thuế và không được khấu trừ thuế đầu vào). Quy định cơ chế phối hợp giữa Bộ Công Thương và Bộ Tài chính để trình Thủ tướng điều chỉnh Danh mục tài nguyên khoáng sản đã chế biến được phép áp dụng thuế suất 0% khi xuất khẩu nhằm khuyến khích chế biến sâu trong nước và bảo vệ tài nguyên quốc gia."),
    
    ("ĐIỀU 4. ĐIỀU KIỆN KHẤU TRỪ THUẾ MUA TRẢ CHẬM, TRẢ GÓP", 
     "Đối với các giao dịch mua hàng hóa, dịch vụ theo phương thức trả chậm, trả góp có giá trị từ 5 triệu đồng trở lên (theo ngưỡng thanh toán không dùng tiền mặt mới), cơ sở kinh doanh căn cứ vào hợp đồng mua bán trả chậm, hóa đơn GTGT để kê khai khấu trừ thuế GTGT đầu vào. Đến thời hạn thanh toán theo hợp đồng, nếu doanh nghiệp không có chứng từ thanh toán không dùng tiền mặt thì phải kê khai điều chỉnh giảm số thuế GTGT đã khấu trừ tương ứng."),
    
    ("ĐIỀU 5. GIA HẠN CHÍNH SÁCH GIẢM THUẾ GTGT 8%", 
     "Tiếp tục triển khai Nghị quyết số 204/2025/QH15 của Quốc hội, chính sách giảm thuế suất thuế GTGT từ 10% xuống 8% đối với các nhóm hàng hóa, dịch vụ đang áp dụng mức thuế suất 10% được tiếp tục kéo dài áp dụng đến hết ngày 31 tháng 12 năm 2026. Một số lĩnh vực đặc thù như viễn thông, công nghệ thông tin, hoạt động tài chính, ngân hàng, chứng khoán, bảo hiểm, kinh doanh bất động sản, kim loại và sản phẩm từ kim loại đúc sẵn, sản phẩm khai khoáng không thuộc diện được giảm thuế GTGT này.")
]

# Write the PDFs to workspace root
create_pdf("thongtu69_2025.pdf", "Thông tư 69/2025/TT-BTC", sections_tt69)
create_pdf("thongtu18_2026.pdf", "Thông tư 18/2026/TT-BTC", sections_tt18)
create_pdf("nghidinh144_2026.pdf", "Nghị định 144/2026/NĐ-CP", sections_nd144)
