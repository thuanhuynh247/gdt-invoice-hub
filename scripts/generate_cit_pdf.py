import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generate_pdf():
    pdf_filename = "vanbanhopnhat61_2026_cit.pdf"
    print(f"Generating {pdf_filename}...")

    # Register Vietnamese font (Tahoma or Arial)
    font_paths = [
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/times.ttf"
    ]
    font_name = "Helvetica" # Default fallback
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont('Tahoma-VN', fp))
                font_name = 'Tahoma-VN'
                print(f"Successfully registered font: {fp}")
                break
            except Exception as e:
                print(f"Failed to register font {fp}: {e}")

    doc = SimpleDocTemplate(pdf_filename, pagesize=letter,
                            rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    # Custom styles supporting custom font
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=18,
        leading=22,
        alignment=1, # Center
        spaceAfter=20
    )
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=8,
        textColor='#1a365d'
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['BodyText'],
        fontName=font_name,
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    story = []
    
    # Document header
    story.append(Paragraph("<b>VĂN BẢN HỢP NHẤT SỐ 61/VBHN-VPQH & THÔNG TƯ 20/2026/TT-BTC</b>", title_style))
    story.append(Paragraph("<b>QUY ĐỊNH LUẬT THUẾ THU NHẬP DOANH NGHIỆP (TNDN) MỚI NHẤT 2025/2026</b>", title_style))
    story.append(Spacer(1, 15))

    # Page 1
    story.append(Paragraph("<b>CHƯƠNG I: BIỂU THUẾ SUẤT THUẾ THU NHẬP DOANH NGHIỆP THEO PHÂN TẦNG DOANH THU</b>", heading_style))
    story.append(Paragraph(
        "Theo Văn bản hợp nhất số 61/VBHN-VPQH ngày 23/03/2026 hợp nhất Luật Thuế TNDN và Nghị định số 320/2025/NĐ-CP, "
        "kể từ kỳ tính thuế TNDN năm 2025/2026 trở đi, Việt Nam chính thức áp dụng thuế suất thuế TNDN phân tầng "
        "dựa trên tổng doanh thu của doanh nghiệp để hỗ trợ doanh nghiệp vừa, nhỏ và siêu nhỏ. Cụ thể:",
        body_style
    ))
    story.append(Paragraph(
        "1. <b>Thuế suất ưu đãi 15%:</b> Áp dụng đối với các doanh nghiệp có tổng doanh thu năm trước liền kề <b>dưới 3 tỷ đồng</b>.",
        body_style
    ))
    story.append(Paragraph(
        "2. <b>Thuế suất ưu đãi 17%:</b> Áp dụng đối với các doanh nghiệp có tổng doanh thu năm trước liền kề <b>từ 3 tỷ đồng đến dưới 50 tỷ đồng</b>.",
        body_style
    ))
    story.append(Paragraph(
        "3. <b>Thuế suất phổ thông 20%:</b> Áp dụng đối với các doanh nghiệp có tổng doanh thu năm trước liền kề <b>từ 50 tỷ đồng trở lên</b> "
        "hoặc các doanh nghiệp không thuộc đối tượng được hưởng ưu đãi thuế suất.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Lưu ý chống tránh thuế:</b> Mức thuế suất ưu đãi 15% và 17% không áp dụng đối với công ty con hoặc các doanh nghiệp "
        "có mối quan hệ liên kết mà doanh nghiệp trong mối quan hệ liên kết đó không đáp ứng đủ các điều kiện áp dụng ưu đãi này. "
        "Quy định này nhằm ngăn chặn các hành vi chia tách nhỏ doanh nghiệp để lách thuế.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Page 2
    story.append(Paragraph("<b>CHƯƠNG II: ĐIỀU KIỆN KHẤU TRỪ CHI PHÍ ĐƯỢC TRỪ KHI TÍNH THUẾ TNDN</b>", heading_style))
    story.append(Paragraph(
        "Điều 9 Luật Thuế TNDN và Thông tư số 20/2026/TT-BTC quy định các khoản chi của doanh nghiệp chỉ được tính vào chi phí được trừ "
        "khi đáp ứng toàn bộ các điều kiện sau:",
        body_style
    ))
    story.append(Paragraph(
        "a) Khoản chi thực tế phát sinh liên quan trực tiếp đến hoạt động sản xuất, kinh doanh của doanh nghiệp.",
        body_style
    ))
    story.append(Paragraph(
        "b) Có đầy đủ hóa đơn, chứng từ hợp pháp theo quy định của pháp luật.",
        body_style
    ))
    story.append(Paragraph(
        "c) Có chứng từ thanh toán không dùng tiền mặt đối với các khoản chi có hóa đơn từ 5 triệu đồng trở lên (giá đã bao gồm thuế GTGT). "
        "Ngưỡng thanh toán không dùng tiền mặt này được hạ từ 20 triệu đồng xuống còn <b>5 triệu đồng</b> để tăng cường minh bạch.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Quy định chi ủy quyền cho người lao động thanh toán (Điều 13 Thông tư 20/2026/TT-BTC):</b> "
        "Trường hợp doanh nghiệp ủy quyền cho cá nhân là người lao động của doanh nghiệp thanh toán bằng thẻ cá nhân hoặc tiền mặt từ 5 triệu đồng trở lên, "
        "doanh nghiệp vẫn được tính vào chi phí được trừ nếu có đủ hóa đơn mang tên và mã số thuế của doanh nghiệp, chứng từ chuyển khoản từ tài khoản "
        "cá nhân sang người bán, và chứng từ doanh nghiệp hoàn trả tiền qua tài khoản ngân hàng của cá nhân đó.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Page 3
    story.append(Paragraph("<b>CHƯƠNG III: CÁC KHOẢN CHI PHÍ ĐẶC THÙ ĐƯỢC ƯU ĐÃI KHẤU TRỪ</b>", heading_style))
    story.append(Paragraph(
        "Thông tư 20/2026/TT-BTC bổ sung và làm rõ hồ sơ chứng từ của các khoản chi đặc thù nhằm thúc đẩy chuyển đổi số và chuyển đổi xanh:",
        body_style
    ))
    story.append(Paragraph(
        "1. <b>Chi phí đào tạo nghề nghiệp cho nhân viên:</b> Để được tính vào chi phí được trừ, doanh nghiệp cần có: hợp đồng lao động "
        "hoặc quy chế tài chính quy định chính sách đào tạo; quyết định cử đi học của doanh nghiệp; hồ sơ đăng ký học, hóa đơn học phí và "
        "chứng chỉ hoặc văn bằng xác nhận đã hoàn thành khóa học.",
        body_style
    ))
    story.append(Paragraph(
        "2. <b>Chi phí giảm phát thải khí nhà kính (Net Zero):</b> Nhằm phục vụ mục tiêu chuyển đổi xanh, doanh nghiệp được tính vào "
        "chi phí được trừ các khoản chi thực tế liên quan đến giảm phát thải khi có đầy đủ: quyết định của người có thẩm quyền phê duyệt "
        "kế hoạch giảm phát thải; hồ sơ dự án/đề án chuyển đổi công nghệ; và hóa đơn, chứng từ thanh toán hợp lệ.",
        body_style
    ))
    story.append(Paragraph(
        "3. <b>Chi nghiên cứu khoa học, đổi mới sáng tạo, chuyển đổi số (Digital Transformation):</b> Các khoản chi phát triển phần mềm, "
        "mua bản quyền công nghệ, số hóa dữ liệu và hạ tầng điện toán đám mây phục vụ kinh doanh được khấu trừ toàn bộ theo quy định.",
        body_style
    ))
    story.append(Paragraph(
        "4. <b>Bảng kê mua hàng nông, lâm, thủy sản (Mẫu 02/TNDN):</b> Doanh nghiệp thu mua nông, lâm, thủy sản chưa qua chế biến "
        "trực tiếp từ người dân tự sản xuất bán ra được lập bảng kê chi phí được trừ. Tuy nhiên, các khoản chi trả từng lần từ 5 triệu đồng trở lên "
        "cho mỗi cá nhân vẫn bắt buộc phải có chứng từ thanh toán không dùng tiền mặt.",
        body_style
    ))

    doc.build(story)
    print(f"Successfully generated {pdf_filename}")

if __name__ == "__main__":
    generate_pdf()
