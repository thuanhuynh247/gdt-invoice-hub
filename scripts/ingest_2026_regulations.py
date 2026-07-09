# -*- coding: utf-8 -*-
"""
Ingest 2026 Vietnamese Tax Decrees (252, 253, 254, 255) into RAG database.
"""
from __future__ import annotations
import os
import sys
import sqlite3
from datetime import datetime

# Adjust path to import invoices modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from invoices.tax_crawler_service import ingest_crawled_content

DECREES = {
    "Nghị định số 252/2026/NĐ-CP": {
        "title": "nghidinh252_2026.pdf",
        "date": "2026-07-01",
        "text": """Nghị định số 252/2026/NĐ-CP về kê khai thuế và hoàn thuế có hiệu lực từ ngày 01/07/2026.
Nghị định này thay thế các Nghị định trước đây: Nghị định số 373/2025/NĐ-CP (quy định và biểu mẫu về kê khai quyết toán thuế), Nghị định số 117/2025/NĐ-CP (chủ sàn TMĐT chịu trách nhiệm nộp thay thuế cho các shop online), Nghị định số 49/2025/NĐ-CP (ngưỡng nợ thuế bị tạm hoãn xuất cảnh áp dụng từ 28/2/2025), Nghị định số 91/2022/NĐ-CP (quy định hạn mức tạm nộp thuế TNDN), và Nghị định số 126/2020/NĐ-CP (quy định chung về quản lý thuế).

1. Những quy định và nguyên tắc hoàn toàn mới:
- Quy định cụ thể và đơn giản hóa chế độ ưu tiên đối với người nộp thuế có giao dịch liên kết, bao gồm việc ưu tiên xử lý hồ sơ thỏa thuận trước về phương pháp xác định giá tính thuế (APA).
- Gỡ bỏ hoàn toàn quy định về doanh nghiệp ưu tiên trong lĩnh vực hải quan trong nghị định này.
- Gỡ bỏ cơ chế ủy nhiệm thu thuế trước đây.

2. Những thay đổi trong quy định trước đó:
- Tạm nộp thuế TNDN và lợi nhuận sau thuế: Tổng số thuế TNDN hoặc lợi nhuận sau thuế đã tạm nộp của 4 quý không được thấp hơn 80% số phải nộp theo quyết toán năm. (Thay đổi so với mức 80% của 3 quý đầu năm ở Nghị định 91/2022/NĐ-CP).
- Ngưỡng nợ thuế và thời gian nợ để áp dụng biện pháp tạm hoãn xuất cảnh: Trình tự, thủ tục thông báo tạm hoãn xuất cảnh được quy định rõ ràng, chi tiết hơn để tránh lạm dụng, bảo đảm quyền lợi người nộp thuế.
- Quản lý thuế TMĐT: Chủ sàn thương mại điện tử chịu trách nhiệm khai nộp thay, khấu trừ thuế trực tiếp cho các shop online kinh doanh trên sàn.
- Thời hạn thông báo tạm ngừng kinh doanh và thời hạn thay đổi thông tin đăng ký thuế của cá nhân được điều chỉnh linh hoạt hơn.
- Khai bổ sung hồ sơ khai thuế khi thay đổi kỳ tính thuế từ quý sang tháng: Hướng dẫn chi tiết cách lập và nộp tờ khai bổ sung.
- Hoàn thành nghĩa vụ thuế khi chuyển đổi loại hình doanh nghiệp: Trách nhiệm pháp lý của doanh nghiệp kế thừa và các mốc thời gian chốt số liệu cụ thể.

3. Những lưu ý quan trọng doanh nghiệp cần biết và thay đổi ngay quy trình:
- Thời hạn nộp hồ sơ khai thuế và giới hạn nghiêm ngặt về thời gian cũng như trường hợp được khai bổ sung hồ sơ thuế.
- Đảm bảo ngưỡng tạm nộp thuế TNDN hàng quý đạt từ 80% trở lên cho cả 4 quý để tránh bị phạt tiền chậm nộp thuế 0.03% mỗi ngày.
- Các biện pháp cưỡng chế thuế mới cứng rắn hơn khi người nộp thuế không hoàn thành nghĩa vụ thuế đúng hạn."""
    },
    "Nghị định số 253/2026/NĐ-CP": {
        "title": "nghidinh253_2026.pdf",
        "date": "2026-07-01",
        "text": """Nghị định số 253/2026/NĐ-CP về kê khai và tính thuế Thu nhập cá nhân (TNCN) có hiệu lực từ ngày 01/07/2026.
Nghị định này thay thế Nghị định số 65/2013/NĐ-CP (quy định chi tiết Luật Thuế TNCN từ 1/7/2013).

1. Những thay đổi đáng lưu ý so với NĐ 65/2013/NĐ-CP:
- Tiêu chí xác định cá nhân cư trú được cập nhật rõ ràng hơn dựa trên số ngày có mặt thực tế và nơi ở thường trú hoặc thuê nhà tại Việt Nam.
- Quy định chi tiết các khoản thu nhập chịu thuế từ tiền lương, tiền công, bao gồm các khoản lợi ích bằng tiền hoặc không bằng tiền do người sử dụng lao động trả thay.
- Cập nhật quy định giảm trừ gia cảnh cho bản thân người nộp thuế và người phụ thuộc. Điều kiện đăng ký và hồ sơ chứng minh người phụ thuộc được đơn giản hóa.
- Thuế suất đối với chuyển nhượng vốn (không phải chứng khoán): Áp dụng mức thuế suất 20% trên thu nhập tính thuế.
- Thuế suất chuyển nhượng chứng khoán: Áp dụng thống nhất thuế suất 0.1% trên giá chuyển nhượng chứng khoán mỗi lần giao dịch.
- Thuế suất chuyển nhượng bất động sản: Áp dụng thuế suất thống nhất 2% trên giá chuyển nhượng bất động sản.
- Ngưỡng thu nhập vãng lai không phải quyết toán thuế và ngưỡng khấu trừ 10% đối với thu nhập vãng lai hoặc ngắn hạn được điều chỉnh tăng lên nhằm giảm thiểu thủ tục hành chính cho người lao động có thu nhập thấp.
- Xử lý thuế khi cá nhân góp vốn bằng tài sản vào doanh nghiệp: Thời điểm tính thuế và ghi nhận thu nhập từ chuyển nhượng vốn được hoãn cho đến khi cá nhân thực tế chuyển nhượng phần vốn góp đó.
- Kỳ tính thuế đối với người nước ngoài là cá nhân cư trú được tính theo năm dương lịch hoặc 12 tháng liên tục kể từ ngày đầu tiên có mặt tại Việt Nam.

2. Gỡ bỏ một số phương pháp tính thuế cũ không còn phù hợp:
- Gỡ bỏ phương pháp tính thuế 25% trên thu nhập tính thuế đối với chuyển nhượng bất động sản (chỉ còn áp dụng duy nhất phương pháp thuế suất 2% trên giá bán).
- Gỡ bỏ phương pháp tính thuế 20% trên thu nhập tính thuế đối với chuyển nhượng chứng khoán (chỉ còn áp dụng duy nhất thuế suất 0.1% trên giá bán).
- Gỡ bỏ quy định trực tiếp về việc cơ quan thuế ấn định tỷ lệ thu nhập chịu thuế đối với cá nhân kinh doanh không thực hiện đúng chế độ kế toán, hóa đơn, chứng từ.

3. Các mức khống chế của thu nhập không chịu thuế TNCN:
- Khoán chi văn phòng phẩm, công tác phí, điện thoại, trang phục được trừ theo quy chế của doanh nghiệp nhưng không vượt quá định mức quy định.
- Các khoản phụ cấp, trợ cấp theo quy định của pháp luật về lao động và bảo hiểm xã hội.
- Tiền ăn giữa ca, ăn trưa không vượt quá mức quy định của Bộ Lao động - Thương binh và Xã hội.
- Tiền thuê nhà, dịch vụ kèm theo do người sử dụng lao động trả thay được tính vào thu nhập chịu thuế nhưng không vượt quá 15% tổng thu nhập chịu thuế (chưa bao gồm tiền thuê nhà).
- Hỗ trợ khám chữa bệnh hiểm nghèo cho bản thân người lao động và thân nhân.
- Bảo hiểm hưu trí bổ sung, hưu trí tự nguyện, bảo hiểm nhân thọ được trừ khỏi thu nhập chịu thuế trước khi tính thuế TNCN.
- Bổ sung quy định mới về giảm trừ chi phí y tế và giáo dục - đào tạo thực tế có chứng từ hợp pháp cho bản thân người nộp thuế, với tổng mức giảm trừ mới tối đa cho y tế và giáo dục được nâng lên đáng kể.
- Thu nhập từ trúng thưởng, bản quyền, nhượng quyền thương mại, thừa kế, quà tặng chịu thuế suất lũy tiến hoặc thuế suất toàn phần tùy loại hình.

4. Bổ sung các khoản thu nhập chịu thuế, miễn thuế và các khoản giảm trừ mới:
- Quy định cụ thể thời điểm tính thuế TNCN đối với cổ phiếu thưởng và quyền mua cổ phiếu là thời điểm cá nhân thực hiện bán/chuyển nhượng cổ phiếu thưởng hoặc thực hiện quyền mua cổ phiếu.
- Thay đổi các thủ tục và điều kiện bắt buộc liên quan đến chứng từ khấu trừ thuế TNCN điện tử và hồ sơ chứng minh giảm trừ gia cảnh."""
    },
    "Nghị định số 255/2026/NĐ-CP": {
        "title": "nghidinh255_2026.pdf",
        "date": "2026-07-01",
        "text": """Nghị định số 255/2026/NĐ-CP về quản lý thuế đối với doanh nghiệp có giao dịch liên kết (GDLK) có hiệu lực từ ngày 01/07/2026.
Nghị định này thay thế Nghị định số 132/2020/NĐ-CP và Nghị định số 20/2025/NĐ-CP.

1. Những quy định và nội dung hoàn toàn mới:
- Gỡ bỏ định nghĩa "Cơ sở dữ liệu của Cơ quan thuế" nhằm tăng tính minh bạch và khuyến khích doanh nghiệp sử dụng các nguồn dữ liệu độc lập, khách quan để so sánh giá.
- Gỡ bỏ các quy định chuyển tiếp cho kỳ tính thuế 2017, 2018, 2019 (do đã hết thời hạn áp dụng thực tế).

2. Những thay đổi trong quy định trước đó được sửa đổi, bổ sung:
- Định nghĩa rõ ràng hơn về "Giao dịch liên kết" và "Cơ sở dữ liệu thương mại" được công nhận để phục vụ mục đích so sánh giá độc lập.
- Làm rõ các căn cứ để xác định hai doanh nghiệp có quan hệ liên kết (ví dụ: bổ sung quy định cụ thể rằng khoản vay vốn từ ngân hàng thương mại độc lập sẽ không còn bị xem là có giao dịch liên kết nếu không thuộc trường hợp chỉ định điều hành hoặc chiếm tỷ lệ chi phối vốn).
- Điều chỉnh ngưỡng doanh thu để nộp Báo cáo lợi nhuận liên quốc gia (CbCR) phù hợp với chuẩn mực quốc tế BEPS của OECD.
- Ngưỡng doanh thu miễn lập Hồ sơ xác định giá giao dịch liên kết (áp dụng chức năng đơn giản hóa) giúp doanh nghiệp quy mô nhỏ giảm chi phí tuân thủ.
- Nghĩa vụ kê khai của người nộp thuế và trách nhiệm của Ngân hàng Nhà nước trong việc chia sẻ thông tin dòng tiền liên quốc gia để chống chuyển giá.

3. Những lưu ý doanh nghiệp phải biết và thay đổi ngay quy trình:
- Nguyên tắc cốt lõi: Điều chỉnh giá giao dịch liên kết không được làm giảm nghĩa vụ thuế TNDN phải nộp tại Việt Nam.
- Giới hạn chi phí lãi vay được trừ khi tính thuế TNDN (trần EBITDA): Chi phí lãi vay ròng sau khi trừ lãi tiền gửi và lãi cho vay được trừ không vượt quá 30% của tổng chỉ số EBITDA của doanh nghiệp trong kỳ tính thuế.
- Quy định chi tiết các loại chi phí không được khấu trừ khi xác định giá giao dịch liên kết.
- Kê khai thuế phải dựa trên bản chất giao dịch thực tế thay vì hình thức hình thức pháp lý của giao dịch.
- Thời hạn nghiêm ngặt để cung cấp Hồ sơ xác định giá giao dịch liên kết khi có yêu cầu thanh tra, kiểm tra thuế từ cơ quan quản lý (thường là 15 ngày làm việc)."""
    },
    "Nghị định số 254/2026/NĐ-CP": {
        "title": "nghidinh254_2026.pdf",
        "date": "2026-07-01",
        "text": """Nghị định số 254/2026/NĐ-CP về hóa đơn điện tử và chứng từ điện tử có hiệu lực từ ngày 01/07/2026.
Nghị định này thay thế Nghị định số 123/2020/NĐ-CP và Nghị định số 70/2025/NĐ-CP.

1. Những thay đổi đáng lưu ý so với NĐ 70/2025/NĐ-CP và NĐ 123/2020/NĐ-CP:
- Người bán có quyền yêu cầu sàn thương mại điện tử cung cấp dữ liệu định danh, thông tin giao dịch của người mua để phục vụ việc lập hóa đơn điện tử chính xác.
- Quy định rõ ràng trách nhiệm của bên ủy nhiệm và bên nhận ủy nhiệm lập hóa đơn điện tử, tránh tranh chấp pháp lý về thời điểm lập và chịu trách nhiệm nội dung hóa đơn.
- Cơ chế khen thưởng đối với người tiêu dùng tố giác hành vi của doanh nghiệp hoặc hộ kinh doanh không xuất hóa đơn điện tử khi bán hàng hóa, dịch vụ.
- Hóa đơn điện tử do người mua yêu cầu và nhận được là cơ sở pháp lý duy nhất để xác định nghĩa vụ thuế đầu ra của người bán và khấu trừ thuế đầu vào của người mua.

2. Những quy định mới cần tuân thủ nghiêm ngặt:
- Định nghĩa rõ ràng và hình thức xử lý nghiêm khắc đối với hành vi sử dụng "hóa đơn, chứng từ giả" hoặc "sử dụng hóa đơn, chứng từ không hợp pháp" và "sử dụng không hợp pháp hóa đơn".
- Quy định xử lý trường hợp hóa đơn điện tử thiếu một số thông tin bắt buộc của người mua nhưng vẫn đảm bảo tính hợp lệ nếu có mã xác thực của cơ quan thuế.
- Giới hạn hiệu lực của bản giấy chuyển đổi từ hóa đơn điện tử: Bản giấy chuyển đổi chỉ có giá trị lưu giữ, đối chiếu thông tin chứ không có giá trị thanh toán hay dùng để kê khai khấu trừ thuế, ngoại trừ một số trường hợp đặc thù theo hướng dẫn của Bộ Tài chính.
- Nghiêm cấm lạm dụng dữ liệu hóa đơn được ủy nhiệm cho các mục đích thương mại ngoài phạm vi thỏa thuận.
- Quy định thời hạn cuối cùng sử dụng biên lai giấy tự in, đặt in và xử lý chuyển tiếp biên lai thuế.
- Hóa đơn đặt in của cơ quan thuế hết hoàn toàn giá trị sử dụng.
- Bắt buộc lập hóa đơn điện tử cho từng lần bán hàng đối với người mua lẻ (không được gộp chung doanh thu cuối ngày đối với các ngành hàng ăn uống, bán lẻ, xăng dầu).

3. Các quy định cụ thể khác:
- Giải thích rõ định nghĩa “hóa đơn điện tử khởi tạo từ máy tính tiền” có kết nối chuyển dữ liệu điện tử với cơ quan thuế.
- Đối tượng được sử dụng hóa đơn điện tử không có mã của cơ quan thuế được thu hẹp lại, ưu tiên chuyển sang sử dụng hóa đơn có mã để kiểm soát dòng tiền tốt hơn.
- Thời điểm lập hóa đơn điện tử đối với xuất khẩu hàng hóa là thời điểm hoàn thành thủ tục hải quan và chuyển giao quyền sở hữu hàng hóa.
- Thời điểm lập hóa đơn đối với hoạt động casino, kinh doanh trò chơi điện tử có thưởng."""
    }
}

def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.db")
    if not os.path.exists(db_path):
        print(f"Error: {db_path} does not exist. Cannot ingest.")
        return

    # Delete old records with these document names to avoid duplication on re-run
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for name, info in DECREES.items():
        doc_source = info["title"]
        # Delete from chunks table
        cur.execute("DELETE FROM tax_regulation_chunk WHERE document_source = ?", (doc_source,))
        # Delete from FTS5 virtual table if it exists
        try:
            cur.execute("DELETE FROM tax_regulation_fts WHERE document_source = ?", (doc_source,))
        except Exception:
            pass
    conn.commit()
    conn.close()
    print("Cleared any existing records for the 2026 decrees to avoid duplicates.")

    # Now ingest via tax_crawler_service
    for name, info in DECREES.items():
        print(f"Ingesting {name}...")
        result = ingest_crawled_content(
            url="http://local-tax-authority/decree-update-2026",
            custom_title=info["title"],
            text=info["text"],
            effective_date=info["date"]
        )
        if result.get("success"):
            print(f"Successfully ingested {name}: {result['chunks_count']} chunks indexed.")
        else:
            print(f"Failed to ingest {name}: {result.get('error')}")

if __name__ == "__main__":
    main()
