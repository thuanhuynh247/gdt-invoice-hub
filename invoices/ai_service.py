"""AI-powered e-invoice compliance auditing service."""

from __future__ import annotations

import json
import logging
from datetime import datetime
import requests

from extensions import db
from invoices.models import Invoice, LineItem, AIAuditResult
from invoices.scheduler import load_scheduler_settings
from auth.crypto import decrypt_password

logger = logging.getLogger(__name__)


TAX_REGULATIONS = [
    {
        "id": "vat_law_48_2024",
        "title": "Luật Thuế GTGT số 48/2024/QH15 (Hiệu lực từ 01/07/2025)",
        "content": (
            "Luật Thuế giá trị gia tăng số 48/2024/QH15 ban hành ngày 29/11/2024 có hiệu lực thi hành từ ngày 01/07/2025. Các thay đổi chính bao gồm:\n"
            "1. Khấu trừ thuế nộp thay đối với nhà cung cấp nước ngoài (NCCNN): Bổ sung quy định rõ ràng về trách nhiệm của các bên (sàn thương mại điện tử, cổng thanh toán hoặc ngân hàng thương mại) trong việc khấu trừ và nộp thay thuế GTGT đối với dịch vụ số/e-commerce của nhà cung cấp nước ngoài (như Google, Meta, AWS, Microsoft, Zoom) không có cơ sở thường trú tại Việt Nam.\n"
            "2. Điều kiện khấu trừ đầu vào bắt buộc không dùng tiền mặt: Ngưỡng bắt buộc thanh toán không dùng tiền mặt đối với giao dịch mua vào để được khấu trừ thuế GTGT được hạ xuống còn từ 5 triệu đồng trở lên (thay vì ngưỡng 20 triệu đồng trước đây).\n"
            "3. Sửa đổi điều kiện hoàn thuế đối với dự án đầu tư và doanh nghiệp xuất khẩu để tránh trục lợi thuế, quy định chặt chẽ hồ sơ và quy trình hậu kiểm."
        ),
        "keywords": ["luật 48", "luat 48", "2024/qh15", "48/2024", "luật mới", "luat moi", "1/7/2025", "01/07/2025", "nhà cung cấp nước ngoài", "nccnn", "nhà thầu", "nha thau", "thuế nhà thầu", "thương mại điện tử", "sàn giao dịch", "google", "meta", "aws", "microsoft"]
    },
    {
        "id": "vat_law_149_2025",
        "title": "Luật sửa đổi bổ sung Luật Thuế GTGT số 149/2025/QH15 (Hiệu lực từ 01/01/2026)",
        "content": (
            "Luật số 149/2025/QH15 được Quốc hội thông qua ngày 11/12/2025 và có hiệu lực thi hành từ ngày 01/01/2026. Đây là luật cực kỳ quan trọng sửa đổi, bổ sung trực tiếp Luật Thuế GTGT 48/2024/QH15. Các sửa đổi bao gồm:\n"
            "1. Nâng ngưỡng doanh thu hàng năm không chịu thuế GTGT của hộ, cá nhân kinh doanh: Nâng mức doanh thu tối thiểu không thuộc diện chịu thuế GTGT từ 200 triệu đồng/năm (theo Luật 48) lên hẳn 500 triệu đồng/năm. Hộ và cá nhân kinh doanh có doanh thu dưới 500 triệu đồng/năm sẽ hoàn toàn không phải nộp thuế GTGT và thuế TNCN.\n"
            "2. Khôi phục miễn thuế GTGT khâu thương mại đối với nông sản thô: Khôi phục việc miễn thuế GTGT đối với sản phẩm trồng trọt, chăn nuôi, thủy sản chưa chế biến thành sản phẩm khác hoặc chỉ qua sơ chế thông thường ở khâu thương mại (mua bán thương mại trung gian). Việc này giúp giảm chi phí sản xuất thức ăn chăn nuôi, dược liệu, phân bón và thúc đẩy nông nghiệp sản xuất.\n"
            "3. Sửa đổi, bổ sung thuế suất đối với một số nhóm phế phẩm, phụ phẩm, phế liệu thu hồi từ quá trình chế biến và đơn giản hóa thủ tục hoàn thuế xuất khẩu."
        ),
        "keywords": ["luật 149", "luat 149", "149/2025", "149/2025/qh15", "sửa đổi 48", "sua doi 48", "500 triệu", "500 trieu", "nửa tỷ", "doanh thu hộ kinh doanh", "hộ kinh doanh", "cá nhân kinh doanh", "nông sản", "nong san", "thức ăn chăn nuôi", "dược liệu", "thủy sản", "chăn nuôi", "trồng trọt", "khâu thương mại", "khau thuong mai"]
    },
    {
        "id": "vat_deduction_general",
        "title": "Điều kiện khấu trừ thuế GTGT đầu vào (Thông tư 219/2013/TT-BTC Điều 15)",
        "content": (
            "Điều kiện khấu trừ thuế GTGT đầu vào bao gồm:\n"
            "1. Có hóa đơn GTGT hợp pháp hoặc chứng từ nộp thuế GTGT khâu nhập khẩu.\n"
            "2. Có chứng từ thanh toán không dùng tiền mặt đối với hàng hóa, dịch vụ mua vào từ 20 triệu đồng trở lên (đã bao gồm thuế GTGT).\n"
            "Theo Luật Thuế GTGT 2024 (có hiệu lực thi hành từ ngày 01/07/2025), ngưỡng bắt buộc thanh toán không dùng tiền mặt đối với giao dịch mua vào được hạ xuống còn từ 5 triệu đồng trở lên.\n"
            "3. Hàng hóa, dịch vụ mua vào phải phục vụ cho hoạt động sản xuất, kinh doanh hàng hóa, dịch vụ chịu thuế GTGT. Các khoản chi mua sắm vật dụng cá nhân, đồ dùng gia đình hoặc các khoản phúc lợi vượt định mức không chứng minh được tính liên quan trực tiếp đến hoạt động kinh doanh của doanh nghiệp thì không được khấu trừ thuế GTGT đầu vào."
        ),
        "keywords": ["khấu trừ", "khau tru", "điều kiện", "dieu kien", "đầu vào", "dau vao", "20 triệu", "20 trieu", "5 triệu", "5 trieu", "tiền mặt", "tien mat", "chuyển khoản", "chuyen khoan", "phục vụ", "kinh doanh", "luật thuế", "luat thue", "khấu trừ thuế"]
    },
    {
        "id": "vat_deduction_car",
        "title": "Khấu trừ thuế GTGT đối với xe ô tô chở người từ 9 chỗ trở xuống (Thông tư 219/2013/TT-BTC Điều 14)",
        "content": (
            "Tài sản cố định là ô tô chở người từ 9 chỗ ngồi trở xuống (ngoại trừ ô tô sử dụng vào kinh doanh vận chuyển hàng hoá, hành khách, kinh doanh du lịch, khách sạn) có trị giá vượt trên 1,6 tỷ đồng (giá chưa có thuế GTGT) thì số thuế GTGT đầu vào tương ứng với phần trị giá vượt trên 1,6 tỷ đồng không được khấu trừ.\n"
            "Phần giá trị vượt trên 1,6 tỷ đồng này cũng sẽ không được tính khấu hao vào chi phí được trừ khi tính thuế TNDN."
        ),
        "keywords": ["ô tô", "o to", "9 chỗ", "9 cho", "1.6 tỷ", "1,6 tỷ", "1.6 ty", "1,6 ty", "xe con", "xe du lịch", "phương tiện", "khấu hao", "tài sản cố định"]
    },
    {
        "id": "einvoice_timing",
        "title": "Thời điểm lập hóa đơn điện tử (Nghị định 123/2020/NĐ-CP Điều 9)",
        "content": (
            "Thời điểm lập hóa đơn điện tử được quy định như sau:\n"
            "- Đối với bán hàng hóa: là thời điểm chuyển giao quyền sở hữu hoặc quyền sử dụng hàng hóa cho người mua, không phân biệt đã thu được tiền hay chưa.\n"
            "- Đối với cung cấp dịch vụ: là thời điểm hoàn thành việc cung cấp dịch vụ hoặc thời điểm thu tiền trước/trong khi cung cấp dịch vụ.\n"
            "- Trường hợp ngày ký số (signing_date) muộn hơn ngày lập (date) từ 1 ngày trở lên được coi là hóa đơn ký chậm. Doanh nghiệp phát sinh hóa đơn ký chậm có thể bị xử phạt hành chính về thuế/hóa đơn theo Nghị định 125/2020/NĐ-CP và chịu rủi ro bị cơ quan thuế bóc tách thời điểm kê khai khấu trừ đầu vào/đầu ra."
        ),
        "keywords": ["thời điểm", "thoi diem", "lập hóa đơn", "lap hoa don", "ngày lập", "ngày ký", "ngày ký số", "ký chậm", "ky cham", "ký số", "ky so", "nhà cung cấp", "sai thời điểm"]
    },
    {
        "id": "vat_reduction_8",
        "title": "Chính sách giảm thuế GTGT xuống 8% (Nghị định 94/2023/NĐ-CP & Nghị định 72/2024/NĐ-CP)",
        "content": (
            "Chính sách giảm thuế suất GTGT từ 10% xuống 8% áp dụng cho các nhóm hàng hóa, dịch vụ chịu thuế suất 10%, ngoại trừ một số nhóm hàng hóa dịch vụ chịu thuế tiêu thụ đặc biệt, hoặc thuộc các danh mục loại trừ: viễn thông, hoạt động tài chính, ngân hàng, chứng khoán, bảo hiểm, kinh doanh bất động sản, kim loại và sản phẩm từ kim loại đúc sẵn, sản phẩm khai khoáng, than cốc, dầu mỏ tinh chế, hóa chất và sản phẩm hóa chất, và công nghệ thông tin.\n"
            "Các mặt hàng này khi xuất hóa đơn vẫn phải áp dụng thuế suất 10%, không được giảm xuống 8%."
        ),
        "keywords": ["8%", "tám phần trăm", "giảm thuế", "giam thue", "giảm gtgt", "thuế suất", "thue suat", "10%", "loại trừ", "danh mục", "công nghệ thông tin", "ngân hàng"]
    },
    {
        "id": "einvoice_errors",
        "title": "Xử lý hóa đơn điện tử có sai sót (Nghị định 123/2020/NĐ-CP Điều 19)",
        "content": (
            "Biện pháp xử lý hóa đơn điện tử có sai sót:\n"
            "1. Hóa đơn chưa gửi cho người mua: Người bán hủy hóa đơn cũ, thông báo cơ quan thuế theo Mẫu 04/SS-HĐĐT và lập hóa đơn mới thay thế.\n"
            "2. Hóa đơn đã gửi cho người mua nhưng chỉ sai tên, địa chỉ (không sai MST, các nội dung khác): Người bán thông báo cho người mua về việc sai sót và gửi Mẫu 04/SS-HĐĐT lên cơ quan thuế, không phải lập lại hóa đơn.\n"
            "3. Hóa đơn đã gửi cho người mua có sai MST, sai số tiền, sai thuế suất, tiền thuế hoặc quy cách hàng hóa: Người bán lập hóa đơn điện tử điều chỉnh hoặc hóa đơn thay thế mới gửi cho người mua, đồng thời gửi Mẫu 04/SS-HĐĐT lên cơ quan thuế."
        ),
        "keywords": ["sai sót", "sai sot", "viết sai", "viet sai", "điều chỉnh", "dieu chinh", "thay thế", "thay the", "04/ss-hđđt", "mẫu 04", "mã số thuế", "địa chỉ", "tên người mua", "hóa đơn điều chỉnh"]
    },
    {
        "id": "cit_circular_20_2026",
        "title": "Thông tư số 20/2026/TT-BTC về quản lý thuế thu nhập doanh nghiệp (Hiệu lực từ 12/03/2026)",
        "content": (
            "Thông tư số 20/2026/TT-BTC ban hành ngày 12/02/2026 và có hiệu lực thi hành từ ngày 12/03/2026 hướng dẫn về thuế TNDN. Các thay đổi chính bao gồm:\n"
            "1. Chi phí mua hàng ủy quyền qua cá nhân (Điều 13): Đối với các giao dịch mua hàng, dịch vụ được doanh nghiệp ủy quyền cho cá nhân thanh toán bằng thẻ cá nhân hoặc tiền mặt có giá trị từ 5 triệu đồng trở lên (bao gồm cả thuế GTGT), doanh nghiệp chỉ được tính vào chi phí được trừ khi có đủ hóa đơn hợp pháp và chứng từ thanh toán không dùng tiền mặt (chuyển khoản từ tài khoản cá nhân được ủy quyền sang tài khoản người bán và doanh nghiệp hoàn trả tiền qua tài khoản ngân hàng của cá nhân đó, hoặc chuyển khoản trực tiếp).\n"
            "2. Chi phí không dùng tiền mặt: Thắt chặt quy định chứng từ thanh toán không dùng tiền mặt đối với các khoản chi ủy quyền cá nhân từ 5 triệu đồng trở lên để tránh gian lận chi phí hợp lý."
        ),
        "keywords": ["thông tư 20", "thong tu 20", "20/2026", "20/2026/tt-btc", "ủy quyền", "uy quyen", "thẻ cá nhân", "cá nhân thanh toán", "nhân viên thanh toán", "nhân viên ủy quyền", "5 triệu", "5 trieu"]
    }
]


def get_tax_rag_context(query: str) -> str:
    if not query:
        return ""
    
    from extensions import db
    try:
        # Clean query to prevent SQLite FTS5 special character syntax errors
        import re
        clean_q = re.sub(r'[^\w\s\d]', ' ', query).strip()
        if not clean_q:
            clean_q = query
            
        sql = """
            SELECT chunk_content, document_source, page_number
            FROM tax_regulation_fts
            WHERE tax_regulation_fts MATCH :q
            ORDER BY bm25(tax_regulation_fts) ASC
            LIMIT 3;
        """
        res = db.session.execute(db.text(sql), {"q": clean_q}).fetchall()
        
        if res:
            matches = []
            for row in res:
                content, source, page = row
                matches.append(f"### [{source} - Trang {page}]\n{content}")
            return "\n\n".join(matches)
    except Exception as e:
        logger.warning(f"FTS5 dynamic RAG lookup failed: {e}. Falling back to keyword dictionary.")
        
    q_lower = query.lower()
    matches = []
    for reg in TAX_REGULATIONS:
        if any(kw in q_lower for kw in reg["keywords"]):
            matches.append(f"### {reg['title']}\n{reg['content']}")
    
    if matches:
        return "\n\n".join(matches)
    
    return (
        f"### {TAX_REGULATIONS[0]['title']}\n{TAX_REGULATIONS[0]['content']}\n\n"
        f"### {TAX_REGULATIONS[2]['title']}\n{TAX_REGULATIONS[2]['content']}"
    )


def init_fts5_tables():
    """Create the SQLite FTS5 virtual table for full-text search indexing."""
    from extensions import db
    try:
        db.session.execute(db.text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tax_regulation_fts USING fts5(
                chunk_id UNINDEXED,
                chunk_content,
                document_source,
                page_number
            );
        """))
        db.session.commit()
        logger.info("SQLite FTS5 virtual table successfully initialized.")
    except Exception as e:
        logger.error(f"FTS5 virtual table creation failed: {e}")
        db.session.rollback()


def parse_and_chunk_pdf(filename: str) -> list[dict]:
    """Parse local PDF document using pypdf and slice it into clean semantic paragraph chunks."""
    import os
    if not os.path.exists(filename):
        logger.warning(f"PDF document for dynamic ingestion not found: {filename}")
        return []

    from pypdf import PdfReader
    chunks = []
    try:
        reader = PdfReader(filename)
        if "20-btc" in filename:
            effective_date = "2026-03-12"
        elif "48" in filename:
            effective_date = "2025-07-01"
        else:
            effective_date = "2026-01-01"
        
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue
            
            # Clean up Vietnamese text spaces and blank lines
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            full_text = " ".join(lines)
            
            # Split page text into small semantic paragraphs of ~150-250 words
            words = full_text.split(" ")
            current_chunk = []
            word_count = 0
            
            for w in words:
                current_chunk.append(w)
                word_count += 1
                if word_count >= 180 and w.endswith((".", ":", ";")):
                    chunk_str = " ".join(current_chunk).strip()
                    if chunk_str:
                        chunks.append({
                            "document_source": os.path.basename(filename),
                            "page_number": page_idx + 1,
                            "effective_date": effective_date,
                            "chunk_content": chunk_str
                        })
                    current_chunk = []
                    word_count = 0
            
            if current_chunk:
                chunk_str = " ".join(current_chunk).strip()
                if chunk_str:
                    chunks.append({
                        "document_source": os.path.basename(filename),
                        "page_number": page_idx + 1,
                        "effective_date": effective_date,
                        "chunk_content": chunk_str
                    })
    except Exception as e:
        logger.error(f"Failed to parse PDF file {filename}: {e}")
        
    return chunks


def run_dynamic_pdf_ingestion(app):
    """Background startup worker to scan, extract, and ingest workspace PDFs into FTS5 index."""
    import os
    with app.app_context():
        from extensions import db
        from invoices.models import TaxRegulationChunk
        
        init_fts5_tables()
        
        pdf_files = ["luat48.pdf", "luat149.signed.pdf", "20-btc.pdf"]
        ingested_any = False
        
        for filename in pdf_files:
            try:
                base_name = os.path.basename(filename)
                existing_count = TaxRegulationChunk.query.filter_by(document_source=base_name).count()
                
                # Deduplication: skip if already indexed in database
                if existing_count > 0:
                    logger.info(f"PDF {filename} is already ingested ({existing_count} chunks in database). Skipping.")
                    continue
                
                logger.info(f"Starting dynamic text extraction for {filename}...")
                chunks = parse_and_chunk_pdf(filename)
                
                if not chunks:
                    logger.warning(f"No text extracted from PDF {filename}")
                    continue
                
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for c in chunks:
                    db_chunk = TaxRegulationChunk(
                        document_source=c["document_source"],
                        page_number=c["page_number"],
                        effective_date=c["effective_date"],
                        chunk_content=c["chunk_content"],
                        created_at=now_str
                    )
                    db.session.add(db_chunk)
                
                db.session.commit()
                
                # Copy chunks directly to FTS5 virtual table
                all_chunks = TaxRegulationChunk.query.filter_by(document_source=base_name).all()
                for c in all_chunks:
                    db.session.execute(
                        db.text("INSERT INTO tax_regulation_fts (chunk_id, chunk_content, document_source, page_number) VALUES (:cid, :content, :source, :page);"),
                        {"cid": c.id, "content": c.chunk_content, "source": c.document_source, "page": c.page_number}
                    )
                db.session.commit()
                
                logger.info(f"Ingested {filename}: {len(chunks)} chunks registered in dynamic search FTS5 index.")
                ingested_any = True
            except Exception as e:
                logger.error(f"Ingestion worker failed for PDF {filename}: {e}")
                db.session.rollback()
                
        if ingested_any:
            logger.info("Dynamic PDF RAG Ingestion background worker finished successfully.")


def start_dynamic_pdf_ingestion_thread(app):
    """Spawns an asynchronous daemon thread to handle background PDF parsing on startup."""
    import threading
    t = threading.Thread(target=run_dynamic_pdf_ingestion, args=(app,), daemon=True)
    t.start()


class AIComplianceAuditor:
    """Audits invoice line items for VAT deductibility and price anomalies using LLMs."""

    def get_historical_average_price(self, item_name: str) -> float | None:
        """Calculate historical average unit price of items with the exact name (case-insensitive)."""
        try:
            # Query the database for matching line item unit prices
            prices = (
                db.session.query(LineItem.unit_price)
                .filter(db.func.lower(LineItem.item_name) == item_name.lower())
                .all()
            )
            if len(prices) > 1:
                # Average prices excluding the current item if multiple exist
                val_list = [p[0] for p in prices if p[0] > 0]
                if val_list:
                    return sum(val_list) / len(val_list)
        except Exception as e:
            logger.warning(f"Error querying historical average for '{item_name}': {e}")
        return None

    def audit_invoice(self, invoice: Invoice) -> list[AIAuditResult]:
        """Perform AI semantic analysis on invoice items and save results."""
        settings = load_scheduler_settings()
        
        # Guard clause: check if AI auditing is enabled
        if not settings.get("ai_enabled"):
            logger.info("AI auditing is disabled in settings.")
            return []

        # Remove any existing AI warnings for this invoice to prevent duplication
        try:
            AIAuditResult.query.filter_by(invoice_id=invoice.id).delete()
            db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to clear legacy AI results for invoice {invoice.id}: {e}")
            db.session.rollback()

        # Build item catalog with historical prices for prompt
        items_payload = []
        for item in invoice.items:
            avg_price = self.get_historical_average_price(item.item_name)
            items_payload.append({
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount_before_tax": item.amount_before_tax,
                "tax_rate": item.tax_rate,
                "historical_average_price": avg_price if avg_price else "unknown"
            })

        prompt_data = {
            "invoice_id": invoice.id,
            "seller_name": invoice.seller_name,
            "seller_mst": invoice.seller_mst,
            "buyer_name": invoice.buyer_name,
            "buyer_mst": invoice.buyer_mst,
            "total_amount": invoice.total_amount,
            "items": items_payload
        }

        # Retrieve buyer taxpayer profile domain context for enhanced semantic audit
        buyer_profile_context = ""
        from invoices.models import TaxpayerProfile
        if invoice.buyer_mst:
            profile = db.session.get(TaxpayerProfile, invoice.buyer_mst)
            if profile:
                buyer_profile_context = f"Thông tin doanh nghiệp mua hàng (Đang kiểm toán): MST: {profile.mst}, Tên Công ty: {profile.company_name}."
        if not buyer_profile_context and invoice.taxpayer_mst:
            profile = db.session.get(TaxpayerProfile, invoice.taxpayer_mst)
            if profile:
                buyer_profile_context = f"Thông tin doanh nghiệp kiểm toán: MST: {profile.mst}, Tên Công ty: {profile.company_name}."

        system_prompt = settings.get(
            "ai_system_prompt",
            "Bạn là Trợ lý Kiểm toán Thuế chuyên nghiệp tại Việt Nam (Senior Tax Auditor), am hiểu Luật Thuế GTGT Việt Nam, các Nghị định và Thông tư hướng dẫn.\n"
            "Nhiệm vụ của bạn là thực hiện kiểm toán tuân thủ chi tiết từng mặt hàng và điều khoản giao dịch trên hóa đơn để xác định các rủi ro về thuế và khấu trừ thuế GTGT đầu vào.\n\n"
            "Hãy kiểm tra nghiêm ngặt theo các tiêu chí pháp lý sau để xác định chính xác một trong các loại cảnh báo (warning_type):\n"
            "1. RỦI RO TIÊU DÙNG CÁ NHÂN (warning_type: 'personal_purchase'):\n"
            "   - Phát hiện mặt hàng dùng cho mục đích cá nhân, gia đình, phúc lợi không phục vụ trực tiếp cho SXKD (ví dụ: sữa bỉm, thực phẩm tiêu dùng gia đình, mỹ phẩm, bia rượu giải trí, hàng hiệu, đồ dùng gia đình cá nhân).\n"
            "   - Ô tô chở người từ 9 chỗ trở xuống có nguyên giá vượt quá 1.6 tỷ đồng (theo Thông tư 219/2013/TT-BTC) trừ trường hợp doanh nghiệp kinh doanh vận tải/du lịch/khách sạn.\n"
            "2. RỦI RO BIẾN ĐỘNG GIÁ (warning_type: 'price_anomaly'):\n"
            "   - So sánh đơn giá hiện tại với giá trung bình lịch sử ('historical_average_price') được cung cấp. Cảnh báo nếu đơn giá chênh lệch bất thường (tăng hoặc giảm quá 20% so với giá trung bình lịch sử) mà không có lý giải hợp lý.\n"
            "3. RỦI RO SAI LỆCH THỜI ĐIỂM HÓA ĐƠN (warning_type: 'invoice_timing'):\n"
            "   - Kiểm tra ngày lập hóa đơn (date) và ngày ký số (signing_date). Nếu ngày ký số muộn hơn ngày lập từ 1 ngày trở lên, đây là rủi ro hóa đơn ký chậm/lập sai thời điểm theo Điều 9 Nghị định 123/2020/NĐ-CP, có thể bị phạt hành chính theo Nghị định 125/2020/NĐ-CP và trì hoãn thời điểm được khấu trừ thuế đầu vào.\n"
            "4. RỦI RO THANH TOÁN TIỀN MẶT (warning_type: 'cash_payment_risk'):\n"
            "   - Giao dịch có tổng trị giá thanh toán lớn (>= 20 triệu VND hiện tại hoặc >= 5 triệu VND từ 01/07/2025 theo Luật Thuế GTGT 2024) nhưng phương thức thanh toán ghi nhận bằng tiền mặt (TM, Tiền mặt) hoặc không dùng tiền mặt không hợp lệ. Rủi ro không được khấu trừ thuế GTGT đầu vào theo Điều 15 Thông tư 219/2013/TT-BTC.\n"
            "5. RỦI RO THUẾ SUẤT GTGT (warning_type: 'tax_rate_mismatch'):\n"
            "   - Phát hiện áp dụng sai mức thuế suất GTGT (ví dụ: các mặt hàng công nghệ thông tin, viễn thông, hóa chất, bất động sản, chứng khoán... được giảm xuống 8% sai quy định theo Nghị định 72/2024/NĐ-CP, lẽ ra phải chịu mức 10%).\n"
            "6. RỦI RO GIAO DỊCH VÀ CƠ QUAN THUẾ (warning_type: 'suspicious_transaction'):\n"
            "   - Người bán nằm trong danh sách đen cảnh báo của Tổng cục Thuế (GDT Blacklist), hóa đơn khống, sai cấu trúc XML, hoặc các giao dịch có nội dung cực kỳ mập mờ, thiếu minh bạch.\n\n"
            "Chỉ trả về định dạng JSON có cấu trúc chỉ định, không giải thích ngoài lề."
        )

        user_content = (
            "Hãy thực hiện phân tích kiểm toán chi tiết cho hóa đơn sau đây.\n"
            f"{buyer_profile_context}\n"
            f"Thông tin hóa đơn bổ sung:\n"
            f"- Phương thức thanh toán: {invoice.payment_method}\n"
            f"- Ngày lập: {invoice.date}\n"
            f"- Ngày ký số: {invoice.signing_date}\n"
            f"- Trạng thái chữ ký số: {'Đã ký hợp lệ' if invoice.has_signature else 'Không có chữ ký số hoặc chữ ký bị lỗi'}\n"
            f"- Cảnh báo hệ thống hiện có: {json.dumps(invoice.warnings, ensure_ascii=False)}\n\n"
            "Danh sách mặt hàng và dữ liệu giá lịch sử để kiểm tra:\n"
            f"{json.dumps(prompt_data, ensure_ascii=False, indent=2)}\n\n"
            "Hãy trả về kết quả phân tích dưới dạng JSON có cấu trúc sau:\n"
            "{\n"
            "  \"anomalies\": [\n"
            "    {\n"
            "      \"warning_type\": \"personal_purchase\" | \"price_anomaly\" | \"invoice_timing\" | \"cash_payment_risk\" | \"tax_rate_mismatch\" | \"suspicious_transaction\",\n"
            "      \"item_name\": \"Tên chính xác của mặt hàng hoặc để trống nếu áp dụng cho toàn bộ hóa đơn\",\n"
            "      \"explanation\": \"Lời giải thích kiểm toán chi tiết bằng tiếng Việt, trích dẫn cụ thể điều khoản pháp lý quy định (ví dụ: Điều 14, 15 Thông tư 219/2013/TT-BTC, Nghị định 123/2020/NĐ-CP, Nghị định 125/2020/NĐ-CP, Nghị định 72/2024/NĐ-CP) và khuyến nghị biện pháp xử lý hoặc khắc phục chi tiết cho kế toán.\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Nếu tất cả mặt hàng và điều kiện giao dịch đều hoàn toàn hợp lệ, không có rủi ro nào, hãy trả về danh sách trống: {\"anomalies\": []}."
        )

        provider = settings.get("ai_provider", "ollama").lower()
        model_name = settings.get("ai_model_name", "gemma-4")
        api_key_cipher = settings.get("ai_api_key", "")
        api_key = decrypt_password(api_key_cipher) if api_key_cipher else ""

        response_text = ""
        try:
            if provider == "ollama":
                endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
                url = f"{endpoint}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1},
                    "format": "json"
                }
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("message", {}).get("content", "")

            elif provider == "gemini":
                m_name = model_name if model_name else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": f"{system_prompt}\n\n{user_content}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1
                    }
                }
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

            elif provider == "openai":
                m_name = model_name if model_name else "gpt-4o-mini"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": m_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")

            else:
                logger.error(f"Unknown AI provider configured: {provider}")
                return []

        except Exception as e:
            logger.error(f"LLM API request failed ({provider}): {e}")
            return []

        # Parse response JSON and save warnings
        created_results = []
        if response_text:
            try:
                # Clean up any potential markdown wrap
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

                parsed = json.loads(cleaned_text)
                anomalies = parsed.get("anomalies", [])
                
                for item in anomalies:
                    w_type = item.get("warning_type", "personal_purchase")
                    explanation = item.get("explanation", "")
                    item_name = item.get("item_name", "")
                    
                    if not explanation:
                        continue

                    # Programmatic validation 1: Price anomaly threshold check (> 5% deviation)
                    if w_type == "price_anomaly" and item_name:
                        avg_price = self.get_historical_average_price(item_name)
                        if avg_price:
                            matching_line_item = None
                            for li in invoice.items:
                                if li.item_name.lower() == item_name.lower() or item_name.lower() in li.item_name.lower():
                                    matching_line_item = li
                                    break
                            if matching_line_item:
                                diff_ratio = abs(matching_line_item.unit_price - avg_price) / avg_price
                                if diff_ratio < 0.05:
                                    logger.info(
                                        f"Bỏ qua cảnh báo biến động giá cho '{item_name}': "
                                        f"độ lệch thực tế ({diff_ratio:.2%}) dưới ngưỡng tối thiểu 5%."
                                    )
                                    continue

                    # Programmatic validation 2: Non-cash payment threshold compliance verification
                    is_cash_warning = "thanh toán" in explanation.lower() or "tiền mặt" in explanation.lower() or "chuyển khoản" in explanation.lower()
                    if is_cash_warning:
                        threshold = 5000000.0 if ("2024" in explanation or "2025" in explanation) else 20000000.0
                        if invoice.total_amount < threshold:
                            logger.info(
                                f"Bỏ qua cảnh báo thanh toán tiền mặt cho hóa đơn {invoice.id}: "
                                f"tổng trị giá {invoice.total_amount:,.0f} VND dưới ngưỡng quy định {threshold:,.0f} VND."
                            )
                            continue
                    
                    # Prefix with item name for context
                    full_explanation = f"Mặt hàng '{item_name}': {explanation}" if item_name else explanation

                    audit_warning = AIAuditResult(
                        invoice_id=invoice.id,
                        warning_type=w_type,
                        explanation=full_explanation,
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    db.session.add(audit_warning)
                    created_results.append(audit_warning)
                
                invoice.ai_audited = True
                from invoices.service import calculate_invoice_t_score
                calculate_invoice_t_score(invoice)
                db.session.commit()

                logger.info(f"AI audit completed for invoice {invoice.id}. Saved {len(created_results)} warnings.")
                
                # Automatically generate AI correction proposals based on audit results
                try:
                    self.generate_correction_proposals(invoice)
                except Exception as ex:
                    logger.error(f"Failed to automatically generate correction proposals: {ex}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to parse LLM response or save results for invoice {invoice.id}: {e}. Response was: {response_text}")

        return created_results

    def generate_correction_proposals(self, invoice) -> list:
        """Analyze invoice audit results and automatically generate draft correction proposals."""
        from invoices.models import InvoiceCorrectionProposal, AIAuditResult
        from extensions import db
        import json
        from datetime import datetime

        # Remove existing pending proposals to avoid duplication
        try:
            InvoiceCorrectionProposal.query.filter_by(invoice_id=invoice.id, status="pending").delete()
            db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to clear existing proposals: {e}")
            db.session.rollback()

        proposals = []
        warnings = AIAuditResult.query.filter_by(invoice_id=invoice.id).all()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for w in warnings:
            if w.warning_type == "cash_payment_risk":
                orig_pm = invoice.payment_method or "TM"
                p = InvoiceCorrectionProposal(
                    invoice_id=invoice.id,
                    taxpayer_mst=invoice.taxpayer_mst,
                    correction_type="payment_method",
                    original_value=orig_pm,
                    proposed_value="CK",
                    ai_explanation=(
                        f"Giao dịch có tổng giá trị thanh toán lớn ({invoice.total_amount:,.0f} VND) "
                        "nhưng phương thức ghi nhận hiện tại là tiền mặt hoặc không rõ ràng. "
                        "Theo quy định tại Điều 15 Thông tư 219/2013/TT-BTC, bắt buộc phải thanh toán không dùng tiền mặt "
                        "để được khấu trừ thuế GTGT đầu vào và tính vào chi phí được trừ khi xác định thuế TNDN. "
                        "AI Auditor đề xuất chuyển sang Chuyển khoản (CK)."
                    ),
                    status="pending",
                    created_at=now_str,
                    updated_at=now_str
                )
                db.session.add(p)
                proposals.append(p)

            elif w.warning_type == "tax_rate_mismatch":
                item_name = ""
                if "Mặt hàng '" in w.explanation:
                    parts = w.explanation.split("'")
                    if len(parts) > 1:
                        item_name = parts[1]

                orig_payload = {"item_name": item_name, "tax_rate": "8%"}
                prop_payload = {"item_name": item_name, "tax_rate": "10%"}

                p = InvoiceCorrectionProposal(
                    invoice_id=invoice.id,
                    taxpayer_mst=invoice.taxpayer_mst,
                    correction_type="tax_rate",
                    original_value=json.dumps(orig_payload, ensure_ascii=False),
                    proposed_value=json.dumps(prop_payload, ensure_ascii=False),
                    ai_explanation=(
                        f"Phát hiện rủi ro áp dụng sai mức thuế suất GTGT cho mặt hàng '{item_name}'. "
                        "Đề xuất điều chỉnh mức thuế suất từ 8% lên 10% theo quy định tại Nghị định 72/2024/NĐ-CP "
                        "và các thông tư liên quan để tránh bị cơ quan thuế truy thu thuế và xử phạt hành chính khi thanh tra."
                    ),
                    status="pending",
                    created_at=now_str,
                    updated_at=now_str
                )
                db.session.add(p)
                proposals.append(p)

            elif w.warning_type == "personal_purchase":
                item_name = ""
                if "Mặt hàng '" in w.explanation:
                    parts = w.explanation.split("'")
                    if len(parts) > 1:
                        item_name = parts[1]

                orig_payload = {"item_name": item_name, "deductible": True}
                prop_payload = {"item_name": item_name, "deductible": False}

                p = InvoiceCorrectionProposal(
                    invoice_id=invoice.id,
                    taxpayer_mst=invoice.taxpayer_mst,
                    correction_type="non_deductible_expense",
                    original_value=json.dumps(orig_payload, ensure_ascii=False),
                    proposed_value=json.dumps(prop_payload, ensure_ascii=False),
                    ai_explanation=(
                        f"Mặt hàng '{item_name}' có tính chất tiêu dùng cá nhân/phúc lợi gia đình không phục vụ "
                        "hoạt động sản xuất kinh doanh của doanh nghiệp. Đề xuất loại trừ chi phí này khỏi chi phí được trừ "
                        "khi tính thuế TNDN và không thực hiện khấu trừ thuế GTGT đầu vào theo đúng quy định tại Điều 14 Thông tư 219/2013/TT-BTC."
                    ),
                    status="pending",
                    created_at=now_str,
                    updated_at=now_str
                )
                db.session.add(p)
                proposals.append(p)

            elif w.warning_type == "price_anomaly":
                item_name = ""
                if "Mặt hàng '" in w.explanation:
                    parts = w.explanation.split("'")
                    if len(parts) > 1:
                        item_name = parts[1]

                p = InvoiceCorrectionProposal(
                    invoice_id=invoice.id,
                    taxpayer_mst=invoice.taxpayer_mst,
                    correction_type="price_anomaly_review",
                    original_value="unverified",
                    proposed_value="verified_with_contract",
                    ai_explanation=(
                        f"Đơn giá của '{item_name}' chênh lệch bất thường so với dữ liệu lịch sử của hệ thống. "
                        "Đề xuất kiểm tra đối chiếu kỹ với hợp đồng thương mại hoặc báo giá đã duyệt để giải trình biến động giá "
                        "khi cơ quan thuế thanh tra về tính hợp lý của chi phí đầu vào."
                    ),
                    status="pending",
                    created_at=now_str,
                    updated_at=now_str
                )
                db.session.add(p)
                proposals.append(p)

        if proposals:
            try:
                db.session.commit()
                logger.info(f"AI Auditor automatically generated {len(proposals)} correction proposals for invoice {invoice.id}.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to commit correction proposals for invoice {invoice.id}: {e}")

        return proposals

    def _call_llm(self, settings: dict, system_prompt: str, user_content: str, response_format_json: bool = False) -> str:
        provider = settings.get("ai_provider", "ollama").lower()
        model_name = settings.get("ai_model_name", "gemma-4")
        api_key_cipher = settings.get("ai_api_key", "")
        api_key = decrypt_password(api_key_cipher) if api_key_cipher else ""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            if provider == "ollama":
                endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
                url = f"{endpoint}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
                if response_format_json:
                    payload["format"] = "json"
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", "").strip()

            elif provider == "gemini":
                m_name = model_name if model_name else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                prompt_text = f"System Instruction:\n{system_prompt}\n\nUser Input:\n{user_content}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt_text}]
                    }],
                    "generationConfig": {
                        "temperature": 0.1
                    }
                }
                if response_format_json:
                    payload["generationConfig"]["responseMimeType"] = "application/json"
                    
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()

            elif provider == "openai":
                m_name = model_name if model_name else "gpt-4o-mini"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": m_name,
                    "messages": messages,
                    "temperature": 0.1
                }
                if response_format_json:
                    payload["response_format"] = {"type": "json_object"}
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                return f"Unsupported AI provider: {provider}"
        except Exception as e:
            logger.error(f"LLM call failed ({provider}): {e}")
            raise e

    def generate_mitigation_letter(self, invoice: Invoice) -> str:
        """Generate a professional Vietnamese tax explanation letter (Công văn giải trình) based on invoice details and anomalies."""
        settings = load_scheduler_settings()
        ai_enabled = settings.get("ai_enabled", False)
        
        # Gather anomalies
        anomalies_list = []
        for audit_res in invoice.ai_audit_results:
            anomalies_list.append(f"- Cảnh báo [{audit_res.warning_type}]: {audit_res.explanation}")
        
        for warning in invoice.warnings:
            anomalies_list.append(f"- Cảnh báo hệ thống: {warning}")
            
        anomalies_str = "\n".join(anomalies_list) if anomalies_list else "Không phát hiện rủi ro nghiêm trọng trên hệ thống."

        # Get buyer taxpayer profile context
        from invoices.models import TaxpayerProfile
        buyer_name = invoice.buyer_name or "CONG TY CO PHAN CONG NGHE GDT INVOICE HUB"
        buyer_mst = invoice.buyer_mst or "0109999999"
        buyer_address = invoice.buyer_address or "Toa nha Technopark, Gia Lam, TP. Ha Noi"
        
        if invoice.buyer_mst:
            profile = db.session.get(TaxpayerProfile, invoice.buyer_mst)
            if profile:
                buyer_name = profile.company_name
                buyer_mst = profile.mst
                buyer_address = profile.company_name or buyer_address
                
        if invoice.taxpayer_mst:
            profile = db.session.get(TaxpayerProfile, invoice.taxpayer_mst)
            if profile:
                buyer_name = profile.company_name
                buyer_mst = profile.mst

        def generate_local_fallback() -> str:
            from datetime import datetime
            today = datetime.now()
            today_str = f"ngày {today.day:02d} tháng {today.month:02d} năm {today.year}"
            
            # Subtitle and legal defense logic based on warnings
            legal_defenses = []
            has_cash_risk = False
            has_mst_risk = False
            has_timing_risk = False
            has_price_risk = False
            has_tax_risk = False
            
            for w in invoice.ai_audit_results:
                w_type = w.warning_type.lower()
                if "cash" in w_type:
                    has_cash_risk = True
                elif "suspicious" in w_type or "mst" in w_type:
                    has_mst_risk = True
                elif "timing" in w_type or "time" in w_type or "date" in w_type:
                    has_timing_risk = True
                elif "price" in w_type:
                    has_price_risk = True
                elif "tax" in w_type:
                    has_tax_risk = True

            # Standard defenses
            if has_cash_risk:
                legal_defenses.append(
                    "1. Về cảnh báo phương thức thanh toán tiền mặt (giao dịch từ 20 triệu đồng trở lên):\n"
                    "   - Căn cứ quy định tại Điều 15 Thông tư số 219/2013/TT-BTC ngày 31/12/2013 của Bộ Tài chính (được sửa đổi, bổ sung bởi Thông tư số 119/2014/TT-BTC, Thông tư số 151/2014/TT-BTC và Thông tư số 26/2015/TT-BTC):\n"
                    "     Công ty chúng tôi xin xác nhận nghiệp vụ kinh tế phát sinh mua hàng hóa/dịch vụ từ người bán là hoàn toàn có thật. Để đảm bảo điều kiện khấu trừ thuế GTGT và tính chi phí hợp lệ khi quyết toán thuế TNDN, Công ty cam kết đã/sẽ thực hiện việc chuyển tiền thanh toán qua tài khoản ngân hàng của Công ty chúng tôi đến tài khoản ngân hàng đã đăng ký với cơ quan quản lý của nhà cung cấp. Mọi chứng từ chuyển khoản ngân hàng (Ủy nhiệm chi, Giấy báo Nợ) sẽ được lưu giữ đầy đủ trong hồ sơ kế toán."
                )
            if has_mst_risk:
                legal_defenses.append(
                    "2. Về cảnh báo rủi ro hóa đơn từ nhà cung cấp có rủi ro cao về thuế:\n"
                    "   - Căn cứ quy định tại Nghị định số 123/2020/NĐ-CP và hướng dẫn tại Công văn số 2546/TCT-TTKT của Tổng cục Thuế:\n"
                    "     Tại thời điểm giao dịch mua bán phát sinh và ngày ký lập hóa đơn này, nhà cung cấp đang hoạt động bình thường, mã số thuế ở trạng thái hoạt động và hóa đơn được phát hành hợp pháp trên hệ thống hóa đơn điện tử của Tổng cục Thuế. Nghiệp vụ mua bán hàng hóa hoàn toàn diễn ra thực tế, có hợp đồng kinh tế, biên bản giao nhận hàng hóa và chứng từ thanh toán đầy đủ. Công ty chúng tôi đã thực hiện các bước đối chiếu, xác minh thông tin doanh nghiệp kỹ lưỡng và cam kết hoàn toàn tự chịu trách nhiệm trước pháp luật về tính chân thật của hồ sơ."
                )
            if has_timing_risk:
                legal_defenses.append(
                    "3. Về cảnh báo chênh lệch ngày lập và ngày ký số hóa đơn:\n"
                    "   - Căn cứ quy định tại Điều 9 và Điều 10 Nghị định số 123/2020/NĐ-CP và Công văn hướng dẫn của Tổng cục Thuế:\n"
                    "     Trường hợp hóa đơn điện tử có thời điểm ký số khác thời điểm lập hóa đơn thì thời điểm khai thuế đối với người mua là thời điểm lập hóa đơn. Công ty chúng tôi đã tiến hành kê khai, khấu trừ thuế GTGT đầu vào đúng thời điểm lập hóa đơn theo đúng hướng dẫn của cơ quan thuế, đảm bảo không làm thất thoát ngân sách nhà nước."
                )
            if has_price_risk:
                legal_defenses.append(
                    "4. Về cảnh báo biến động đơn giá hàng hóa/dịch vụ mua vào:\n"
                    "   - Đơn giá mua vào của các mặt hàng trên hóa đơn được thỏa thuận tự nguyện giữa hai bên dựa trên quy luật thị trường, chất lượng sản phẩm, dịch vụ đi kèm và thời điểm giao dịch. Sự biến động đơn giá (nếu có) hoàn toàn phù hợp với thực tế kinh tế phát sinh tại thời điểm ký kết hợp đồng thương mại."
                )
            if has_tax_risk:
                legal_defenses.append(
                    "5. Về cảnh báo thuế suất thuế GTGT đầu vào:\n"
                    "   - Thuế suất áp dụng trên hóa đơn tuân thủ đúng quy định tại Luật Thuế GTGT hiện hành và các Nghị định giảm thuế của Chính phủ áp dụng đối với nhóm ngành nghề kinh doanh tương ứng của mặt hàng."
                )
            
            if not legal_defenses:
                legal_defenses.append(
                    "1. Về tính hợp pháp và hợp lệ của hóa đơn:\n"
                    "   - Hóa đơn được lập tuân thủ đầy đủ quy định tại Nghị định số 123/2020/NĐ-CP và Thông tư số 78/2021/TT-BTC. Nghiệp vụ kinh tế phát sinh hoàn toàn thực tế, phục vụ hoạt động sản xuất kinh doanh chịu thuế GTGT của Công ty chúng tôi."
                )

            defenses_str = "\n\n".join(legal_defenses)

            return (
                "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
                "Độc lập - Tự do - Hạnh phúc\n"
                "--------------------\n\n"
                f"Hà Nội, {today_str}\n\n"
                "CÔNG VĂN GIẢI TRÌNH\n"
                "Số: 01/CV-GT-2026\n\n"
                "Kính gửi: Chi cục Thuế Quận/Huyện quản lý trực tiếp\n\n"
                f"Tên doanh nghiệp giải trình: {buyer_name}\n"
                f"Mã số thuế: {buyer_mst}\n"
                f"Địa chỉ trụ sở chính: {buyer_address}\n"
                "Người đại diện theo pháp luật: Ban Giám đốc\n\n"
                "Công ty chúng tôi xin giải trình với Cơ quan Thuế về việc kê khai khấu trừ thuế GTGT đầu vào "
                f"và tính hợp lý của chi phí đối với hóa đơn số {invoice.number or ''}, ký hiệu {invoice.symbol or ''}, ngày lập {invoice.date or ''} "
                f"được xuất bởi nhà cung cấp {invoice.seller_name or ''} (MST: {invoice.seller_mst or ''}) như sau:\n\n"
                f"{defenses_str}\n\n"
                "Cam đoan: Công ty chúng tôi cam kết các nội dung giải trình nêu trên hoàn toàn trung thực, "
                "khách quan và chịu trách nhiệm hoàn toàn trước pháp luật nếu có bất kỳ hành vi gian lận thuế nào.\n\n"
                "Kính mong Quý Cơ quan Thuế xem xét, chấp thuận hồ sơ kê khai của Công ty chúng tôi.\n\n"
                "ĐẠI DIỆN PHÁP LUẬT DOANH NGHIỆP\n"
                "(Ký tên, đóng dấu)"
            )

        if not ai_enabled:
            logger.info("AI Compliance Auditor disabled. Generating high-fidelity rules-based explanation letter fallback.")
            return generate_local_fallback()

        # Build a focused RAG query from the invoice's risk warnings for legal context retrieval
        rag_query_parts = []
        for audit_res in invoice.ai_audit_results:
            w_type = audit_res.warning_type.lower()
            if "cash" in w_type:
                rag_query_parts.append("khấu trừ thuế GTGT thanh toán tiền mặt chuyển khoản ngân hàng")
            elif "suspicious" in w_type or "mst" in w_type:
                rag_query_parts.append("hóa đơn nhà cung cấp rủi ro mã số thuế nghi ngờ")
            elif "timing" in w_type or "date" in w_type:
                rag_query_parts.append("thời điểm lập hóa đơn ký số điện tử")
            elif "price" in w_type:
                rag_query_parts.append("đơn giá hàng hóa biến động bất thường chuyển giá")
        if not rag_query_parts:
            rag_query_parts.append("điều kiện khấu trừ thuế GTGT đầu vào hóa đơn hợp lệ")

        rag_legal_context = get_tax_rag_context(" ".join(rag_query_parts))

        system_prompt = (
            "Bạn là Kế toán trưởng kiêm Chuyên gia tư vấn thuế và pháp lý doanh nghiệp chuyên nghiệp (Senior Tax Compliance Consultant / CFO) tại Việt Nam.\n"
            "Nhiệm vụ của bạn là soạn thảo một Công văn giải trình chính thức bằng tiếng Việt gửi Cơ quan Thuế (Cục Thuế/Chi cục Thuế) để bảo vệ quyền lợi được khấu trừ thuế GTGT đầu vào và tính hợp lệ của chi phí được trừ khi tính thuế TNDN đối với hóa đơn mua vào đang bị nghi ngờ rủi ro.\n\n"
        )

        if rag_legal_context:
            system_prompt += (
                "--- QUY ĐỊNH PHÁP LUẬT LIÊN QUAN (Nguồn: Cơ sở dữ liệu RAG Luật Thuế GTGT) ---\n"
                f"{rag_legal_context}\n\n"
                "Hãy sử dụng các quy định trên để dẫn chiếu chính xác trong phần lập luận giải trình. "
                "Trích dẫn cụ thể Điều, Khoản, tên Luật/Thông tư/Nghị định từ tài liệu RAG.\n\n"
            )

        system_prompt += (
            "Công văn giải trình phải được viết cực kỳ chuyên nghiệp, đúng thể thức văn bản hành chính Việt Nam theo Nghị định 30/2020/NĐ-CP và Thông tư 80/2021/TT-BTC, có cấu trúc chặt chẽ gồm:\n"
            "1. Tiêu ngữ chuẩn: 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM' viết hoa, in đậm, căn giữa. Bên dưới là dòng 'Độc lập - Tự do - Hạnh phúc' viết thường, in đậm, căn giữa, có gạch chân.\n"
            "2. Địa danh và ngày tháng năm làm văn bản giải trình.\n"
            "3. Tên văn bản: 'CÔNG VĂN GIẢI TRÌNH' viết hoa, in đậm, cỡ chữ lớn, kèm theo số công văn (ví dụ: Số: .../CV-GT-2026).\n"
            "4. Phần 'Kính gửi': Chi cục Thuế quản lý trực tiếp doanh nghiệp mua hàng.\n"
            "5. Thông tin doanh nghiệp giải trình (Tên công ty giải trình, Mã số thuế, Địa chỉ trụ sở, Người đại diện pháp luật).\n"
            "6. Nội dung giải trình chi tiết về hóa đơn:\n"
            "   - Số hóa đơn, ngày lập, ký hiệu (ký hiệu mẫu và ký hiệu số), tên người bán (nhà cung cấp), mã số thuế người bán, nội dung hàng hóa dịch vụ mua vào, tổng số tiền chưa thuế, thuế suất, tiền thuế GTGT và tổng cộng tiền thanh toán.\n"
            "7. Lập luận biện minh chi tiết cho từng cảnh báo rủi ro được nêu:\n"
            "   - Giải trình logic chặt chẽ, dẫn chiếu chính xác các điều khoản pháp lý quy định (ví dụ: Điều 14, 15 Thông tư 219/2013/TT-BTC, Nghị định 123/2020/NĐ-CP, Nghị định 125/2020/NĐ-CP, Nghị định 72/2024/NĐ-CP, Luật Thuế GTGT mới, Thông tư 96/2015/TT-BTC).\n"
            "   - Đưa ra lý lẽ thuyết phục khẳng định nghiệp vụ mua bán là hoàn toàn có thật (giao dịch thực tế), hàng hóa/dịch vụ mua vào phục vụ trực tiếp cho hoạt động sản xuất kinh doanh của công ty.\n"
            "8. Lời cam đoan của doanh nghiệp về tính trung thực của hồ sơ giải trình và đề nghị Cơ quan Thuế xem xét chấp thuận cho khấu trừ thuế GTGT và tính chi phí hợp lệ.\n"
            "9. Ký tên: Đại diện pháp luật của doanh nghiệp (ký tên, đóng dấu).\n\n"
            "LƯU Ý QUAN TRỌNG: Không trả về mã markdown ``` hay bất kỳ lời dẫn giải nào ngoài nội dung công văn giải trình bằng tiếng Việt. Bắt đầu thẳng bằng tiêu ngữ."
        )

        user_content = (
            "Hãy soạn thảo Công văn giải trình thuế chi tiết cho hóa đơn sau:\n\n"
            f"--- THÔNG TIN DOANH NGHIỆP GIẢI TRÌNH (BÊN MUA) ---\n"
            f"- Tên Công ty: {buyer_name}\n"
            f"- Mã số thuế: {buyer_mst}\n"
            f"- Địa chỉ: {buyer_address}\n\n"
            f"--- THÔNG TIN HÓA ĐƠN CẦN GIẢI TRÌNH ---\n"
            f"- Số hóa đơn: {invoice.number}\n"
            f"- Ký hiệu: {invoice.symbol}\n"
            f"- Ngày lập: {invoice.date}\n"
            f"- Ngày ký số: {invoice.signing_date}\n"
            f"- Tên bên bán (Nhà cung cấp): {invoice.seller_name}\n"
            f"- MST bên bán: {invoice.seller_mst}\n"
            f"- Địa chỉ bên bán: {invoice.seller_address}\n"
            f"- Trị giá trước thuế: {invoice.amount_before_tax:,.0f} VND\n"
            f"- Thuế GTGT: {invoice.tax_amount:,.0f} VND\n"
            f"- Tổng cộng thanh toán: {invoice.total_amount:,.0f} VND\n"
            f"- Phương thức thanh toán: {invoice.payment_method}\n\n"
            f"--- DANH SÁCH RỦI RO CẦN GIẢI TRÌNH ---\n"
            f"{anomalies_str}\n\n"
            "Hãy viết toàn văn công văn giải trình hoàn chỉnh, chuẩn chỉnh pháp lý, sẵn sàng in ấn."
        )

        try:
            return self._call_llm(settings, system_prompt, user_content, response_format_json=False)
        except Exception as e:
            logger.warning(f"LLM mitigation generation failed: {e}. Falling back to high-fidelity rules-based explanation letter.")
            return generate_local_fallback()


def apply_correction_proposal(proposal) -> bool:
    """Apply the approved correction proposal changes to the related invoice and its line items."""
    from extensions import db
    from invoices.models import Invoice, LineItem
    import json
    from datetime import datetime

    invoice = db.session.get(Invoice, proposal.invoice_id)
    if not invoice:
        logger.error(f"Invoice {proposal.invoice_id} not found for correction proposal {proposal.id}")
        return False

    try:
        if proposal.correction_type == "payment_method":
            invoice.payment_method = proposal.proposed_value

        elif proposal.correction_type == "tax_rate":
            try:
                proposed_data = json.loads(proposal.proposed_value)
                item_name = proposed_data.get("item_name", "")
                tax_rate_str = proposed_data.get("tax_rate", "10%")

                # Find matching line item
                for item in invoice.items:
                    if item.item_name.lower() == item_name.lower() or item_name.lower() in item.item_name.lower():
                        item.tax_rate = tax_rate_str
                        # Parse the numeric rate from the string (e.g. "10%" → 0.10)
                        import re
                        rate_match = re.search(r'(\d+(?:\.\d+)?)', tax_rate_str)
                        rate_val = float(rate_match.group(1)) / 100.0 if rate_match else 0.10

                        item.tax_amount = item.amount_before_tax * rate_val
                        break

                # Recalculate invoice totals
                total_tax = sum(item.tax_amount for item in invoice.items)
                invoice.tax_amount = total_tax
                invoice.total_amount = invoice.amount_before_tax + total_tax
            except Exception as ex:
                logger.error(f"Failed to apply tax_rate correction: {ex}")
                return False

        elif proposal.correction_type == "non_deductible_expense":
            try:
                proposed_data = json.loads(proposal.proposed_value)
                item_name = proposed_data.get("item_name", "")

                for item in invoice.items:
                    if item.item_name.lower() == item_name.lower() or item_name.lower() in item.item_name.lower():
                        item.expense_category = "Chi phí không được trừ"
                        break
            except Exception as ex:
                logger.error(f"Failed to apply non_deductible_expense correction: {ex}")
                return False

        elif proposal.correction_type == "price_anomaly_review":
            # Price anomaly review is purely informational, just mark as approved/reviewed
            pass

        proposal.status = "approved"
        proposal.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.session.commit()
        logger.info(f"Successfully applied correction proposal {proposal.id} to invoice {invoice.id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to apply correction proposal {proposal.id}: {e}")
        return False


class AIChatAgent:
    """Intelligent conversational agent powered by local LLMs (Gemma-4) for invoice querying."""

    def _call_llm(self, settings: dict, system_prompt: str, user_content: str, response_format_json: bool = False) -> str:
        provider = settings.get("ai_provider", "ollama").lower()
        model_name = settings.get("ai_model_name", "gemma-4")
        api_key_cipher = settings.get("ai_api_key", "")
        api_key = decrypt_password(api_key_cipher) if api_key_cipher else ""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            if provider == "ollama":
                endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
                url = f"{endpoint}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
                if response_format_json:
                    payload["format"] = "json"
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", "").strip()

            elif provider == "gemini":
                m_name = model_name if model_name else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                prompt_text = f"System Instruction:\n{system_prompt}\n\nUser Input:\n{user_content}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt_text}]
                    }],
                    "generationConfig": {
                        "temperature": 0.1
                    }
                }
                if response_format_json:
                    payload["generationConfig"]["responseMimeType"] = "application/json"
                    
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()

            elif provider == "openai":
                m_name = model_name if model_name else "gpt-4o-mini"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": m_name,
                    "messages": messages,
                    "temperature": 0.1
                }
                if response_format_json:
                    payload["response_format"] = {"type": "json_object"}
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                return f"Unsupported AI provider: {provider}"
        except Exception as e:
            logger.error(f"LLM call failed ({provider}): {e}")
            raise e

    def _is_sql_safe(self, sql_query: str) -> bool:
        if not sql_query:
            return False
            
        cleaned = sql_query.strip().lower()
        import re
        
        # Remove comments to analyze raw statements
        cleaned_no_comments = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned_no_comments = re.sub(r'--.*$', '', cleaned_no_comments, flags=re.MULTILINE)
        cleaned_no_comments = cleaned_no_comments.strip()
        
        # 1. Must start with SELECT
        if not cleaned_no_comments.startswith("select"):
            return False
            
        # 2. Semicolons check: Semicolons can only end the query. No chaining.
        temp = cleaned_no_comments
        while temp.endswith(';'):
            temp = temp[:-1].strip()
        if ';' in temp:
            return False
            
        # 3. Block list of forbidden modification keywords
        forbidden = [
            "insert", "update", "delete", "drop", "alter", "create", "replace", 
            "truncate", "rename", "pragma", "grant", "revoke", "execute", "exec"
        ]
        for word in forbidden:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, cleaned_no_comments):
                return False
                
        # 4. Check for forbidden table names: only query invoice, line_item, ai_audit_result
        forbidden_tables = ["system_config", "scheduler_log", "ai_chat_session", "ai_chat_message"]
        for table in forbidden_tables:
            pattern = r'\b' + re.escape(table) + r'\b'
            if re.search(pattern, cleaned_no_comments):
                return False
                
        return True

    def ask(self, session_id: str, user_message: str) -> str:
        from invoices.models import AIChatSession, AIChatMessage, Invoice
        from extensions import db
        settings = load_scheduler_settings()

        if not settings.get("ai_enabled"):
            return "Trình trợ lý AI hiện đang bị tắt trong phần Cài đặt. Vui lòng bật AI Settings để bắt đầu hội thoại."

        # Fetch recent chat history in the session
        history = AIChatMessage.query.filter_by(session_id=session_id).order_by(AIChatMessage.id.asc()).all()
        history_context = ""
        for msg in history[-10:]:  # Last 10 messages
            history_context += f"{'Kế toán' if msg.role == 'user' else 'Trợ lý AI'}: {msg.content}\n"

        # Look up if this session is bound to an invoice
        invoice_context = ""
        try:
            session = db.session.get(AIChatSession, session_id)
            if session and session.invoice_id:
                invoice = db.session.get(Invoice, session.invoice_id)
                if invoice:
                    items_detail = []
                    for item in invoice.items:
                        items_detail.append(
                            f"- Tên hàng: {item.item_name}, ĐVT: {item.unit or ''}, Số lượng: {item.quantity or 0}, "
                            f"Đơn giá: {item.unit_price or 0}, Thành tiền (chưa VAT): {item.amount_before_tax or 0}, "
                            f"Thuế suất: {item.tax_rate or ''}, Tiền thuế: {item.tax_amount or 0}, Nhóm chi phí: {item.expense_category or ''}"
                        )
                    warnings_detail = []
                    if invoice.warnings_json:
                        try:
                            warnings_detail = json.loads(invoice.warnings_json)
                        except Exception:
                            pass
                    
                    invoice_context = (
                        f"### THÔNG TIN HÓA ĐƠN THAM VẤN HIỆN TẠI (INVOICE CONTEXT):\n"
                        f"- Mã hệ thống: {invoice.id}\n"
                        f"- Bên bán: {invoice.seller_name} (MST: {invoice.seller_mst})\n"
                        f"- Địa chỉ bên bán: {invoice.seller_address}\n"
                        f"- Bên mua: {invoice.buyer_name} (MST: {invoice.buyer_mst})\n"
                        f"- Địa chỉ bên mua: {invoice.buyer_address}\n"
                        f"- Số hóa đơn: {invoice.number} | Ký hiệu: {invoice.symbol} | Ngày lập: {invoice.date}\n"
                        f"- Tiền hàng trước thuế: {invoice.amount_before_tax:,.2f} {invoice.currency or 'VND'}\n"
                        f"- Tiền thuế GTGT: {invoice.tax_amount:,.2f} {invoice.currency or 'VND'}\n"
                        f"- Tổng thanh toán: {invoice.total_amount:,.2f} {invoice.currency or 'VND'}\n"
                        f"- Hình thức thanh toán: {invoice.payment_method or ''}\n"
                        f"- Điểm rủi ro T-Score: {invoice.t_score}/100 | Xếp hạng: {invoice.t_rating}\n"
                        f"- Cảnh báo hình thức: {', '.join(warnings_detail) if warnings_detail else 'Không có'}\n"
                        f"- Chi tiết mặt hàng:\n" + "\n".join(items_detail) + "\n\n"
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch bound invoice context for chat: {e}")

        # 1. Classify intent
        intent = "general_query"
        try:
            intent_system_prompt = (
                "Bạn là bộ phận phân loại ý định (intent classifier) cho trợ lý hóa đơn.\n"
                "Hãy phân loại câu hỏi của người dùng thành một trong các nhóm sau:\n"
                "- 'sql_query': Khi người dùng hỏi về thống kê dữ liệu hóa đơn, liệt kê danh sách hóa đơn theo điều kiện lọc, tính toán tổng số tiền/thuế, hoặc so sánh đơn giá/chi phí/ngân sách.\n"
                "- 'general_query': Khi người dùng hỏi về quy định pháp luật thuế, chính sách kế toán, cách sử dụng phần mềm, hoặc giải thích luật VAT.\n"
                "- 'chitchat': Khi người dùng chào hỏi, hỏi thăm sức khỏe, hoặc trò chuyện phiếm không liên quan đến công việc.\n\n"
                "Hãy phân loại dựa trên câu hỏi hiện tại và lịch sử hội thoại nếu có.\n"
                "Trả về duy nhất một đối tượng JSON có dạng:\n"
                "{\n  \"intent\": \"sql_query\" | \"general_query\" | \"chitchat\"\n}"
            )
            intent_user_content = f"Lịch sử hội thoại:\n{history_context}\nCâu hỏi hiện tại: {user_message}"
            intent_response = self._call_llm(settings, intent_system_prompt, intent_user_content, response_format_json=True)
            
            cleaned_intent = intent_response.strip()
            if cleaned_intent.startswith("```json"):
                cleaned_intent = cleaned_intent[7:]
            elif cleaned_intent.startswith("```"):
                cleaned_intent = cleaned_intent[3:]
            if cleaned_intent.endswith("```"):
                cleaned_intent = cleaned_intent[:-3]
            cleaned_intent = cleaned_intent.strip()
            
            parsed_intent = json.loads(cleaned_intent)
            intent = parsed_intent.get("intent", "general_query")
        except Exception as e:
            logger.warning(f"Failed to classify intent using LLM: {e}. Falling back to keywords.")
            keywords = ["tổng", "bao nhiêu", "liệt kê", "thống kê", "tìm kiếm", "tìm hóa đơn", "đơn giá", "chi phí", "ngân sách", "lớn hơn", "nhỏ hơn", "tối thiểu", "tối đa", "trung bình", "tổng cộng", "select", "sql", "hóa đơn"]
            if any(kw in user_message.lower() for kw in keywords):
                intent = "sql_query"

        # 2. Process based on intent
        if intent == "sql_query":
            try:
                # Generate SQL
                sql_system_prompt = (
                    "Bạn là trợ lý lập trình SQLite chuyên nghiệp. Nhiệm vụ của bạn là chuyển câu hỏi tiếng Việt của người dùng thành một câu lệnh SQLite SELECT hợp lệ và an sau.\n"
                    "Cơ sở dữ liệu của chúng ta gồm có các bảng sau:\n\n"
                    "1. Bảng `invoice` (Lưu thông tin hóa đơn):\n"
                    "   - `id` TEXT PRIMARY KEY (mã hóa đơn, định dạng: seller_mst-symbol-number)\n"
                    "   - `number` TEXT (số hóa đơn)\n"
                    "   - `date` TEXT (ngày lập hóa đơn, định dạng YYYY-MM-DD)\n"
                    "   - `seller_name` TEXT (tên người bán/nhà cung cấp)\n"
                    "   - `seller_mst` TEXT (mã số thuế người bán)\n"
                    "   - `seller_address` TEXT\n"
                    "   - `buyer_name` TEXT\n"
                    "   - `buyer_mst` TEXT\n"
                    "   - `buyer_address` TEXT\n"
                    "   - `amount_before_tax` REAL (tiền hàng trước thuế)\n"
                    "   - `tax_amount` REAL (tiền thuế GTGT)\n"
                    "   - `total_amount` REAL (tổng cộng tiền thanh toán)\n"
                    "   - `has_signature` INTEGER (1 nếu có chữ ký số, 0 nếu không)\n"
                    "   - `signing_date` TEXT (định dạng YYYY-MM-DD)\n"
                    "   - `payment_method` TEXT (hình thức thanh toán: 'Tiền mặt', 'Chuyển khoản', v.v.)\n"
                    "   - `is_cancelled` INTEGER (1 nếu hóa đơn bị hủy, 0 nếu hoạt động)\n"
                    "   - `cancellation_date` TEXT\n"
                    "   - `due_date` TEXT (ngày đến hạn thanh toán, định dạng YYYY-MM-DD)\n"
                    "   - `paid_date` TEXT (ngày đã thanh toán thực tế, định dạng YYYY-MM-DD)\n"
                    "   - `t_score` INTEGER (điểm rủi ro thuế 0-100)\n"
                    "   - `t_rating` TEXT (xếp hạng tuân thủ A++, A, B, C, D)\n\n"
                    "2. Bảng `line_item` (Lưu thông tin chi tiết các mặt hàng trong hóa đơn):\n"
                    "   - `id` INTEGER PRIMARY KEY AUTOINCREMENT\n"
                    "   - `invoice_id` TEXT (khóa ngoại liên kết với `invoice.id`)\n"
                    "   - `item_name` TEXT (tên mặt hàng)\n"
                    "   - `unit` TEXT (đơn vị tính)\n"
                    "   - `quantity` REAL (số lượng)\n"
                    "   - `unit_price` REAL (đơn giá)\n"
                    "   - `amount_before_tax` REAL\n"
                    "   - `tax_rate` TEXT (thuế suất ví dụ: '8%', '10%', '0%', 'KTSG')\n"
                    "   - `tax_amount` REAL\n"
                    "   - `expense_category` TEXT (nhóm chi phí ví dụ: 'Văn phòng phẩm & Thiết bị văn phòng', 'Thiết bị công nghệ & Phần mềm', v.v.)\n\n"
                    "3. Bảng `ai_audit_result` (Lưu kết quả kiểm toán tuân thủ của AI):\n"
                    "   - `id` INTEGER PRIMARY KEY AUTOINCREMENT\n"
                    "   - `invoice_id` TEXT (khóa ngoại liên kết với `invoice.id`)\n"
                    "   - `warning_type` TEXT ('personal_purchase' hoặc 'price_anomaly')\n"
                    "   - `explanation` TEXT\n"
                    "   - `created_at` TEXT\n\n"
                    "HƯỚNG DẪN QUAN TRỌNG:\n"
                    "- Chỉ tạo một câu lệnh SELECT SQLite duy nhất.\n"
                    "- Không dùng các lệnh thay đổi dữ liệu như INSERT, UPDATE, DELETE, DROP, v.v.\n"
                    "- Khi so sánh ngày tháng (date), hãy nhớ định dạng ngày lưu trữ là YYYY-MM-DD.\n"
                    "- Khi so sánh tên mặt hàng (item_name), sử dụng `LIKE '%tên%'` để tìm kiếm tương đối không phân biệt hoa thường.\n"
                    "- Trả về kết quả dưới dạng JSON thuần túy có định dạng:\n"
                    "{\n  \"sql\": \"câu lệnh SELECT SQLite của bạn\",\n  \"explanation\": \"giải thích ngắn gọn về câu truy vấn bằng tiếng Việt\"\n}"
                )
                sql_user_content = f"Lịch sử hội thoại:\n{history_context}\nCâu hỏi hiện tại: {user_message}"
                sql_response = self._call_llm(settings, sql_system_prompt, sql_user_content, response_format_json=True)
                
                cleaned_sql = sql_response.strip()
                if cleaned_sql.startswith("```json"):
                    cleaned_sql = cleaned_sql[7:]
                elif cleaned_sql.startswith("```"):
                    cleaned_sql = cleaned_sql[3:]
                if cleaned_sql.endswith("```"):
                    cleaned_sql = cleaned_sql[:-3]
                cleaned_sql = cleaned_sql.strip()

                parsed_sql = json.loads(cleaned_sql)
                sql_query = parsed_sql.get("sql", "").strip()
                explanation = parsed_sql.get("explanation", "")
                
                if not sql_query:
                    raise ValueError("Không thể tạo câu lệnh SQL từ yêu cầu.")

                # Check SQL safety
                if not self._is_sql_safe(sql_query):
                    return (
                        "Xin lỗi, tôi đã tạo câu truy vấn SQL nhưng nó không vượt qua được kiểm tra bảo mật "
                        "(chỉ cho phép truy vấn SELECT trên các bảng hóa đơn và không được phép dùng các từ khóa nguy hiểm).\n\n"
                        f"Câu truy vấn bị từ chối: `{sql_query}`"
                    )

                # Execute SQL
                try:
                    result = db.session.execute(db.text(sql_query))
                    rows = [dict(row._mapping) for row in result.all()]
                    # Limit output to 100 rows
                    rows = rows[:100]
                except Exception as db_err:
                    logger.error(f"SQL execution error: {db_err}")
                    return (
                        "Đã xảy ra lỗi khi thực thi câu lệnh SQL được sinh ra. Có thể mô hình AI đã viết sai tên cột hoặc điều kiện truy vấn.\n\n"
                        f"**Truy vấn đã thử:**\n```sql\n{sql_query}\n```\n"
                        f"**Lỗi chi tiết:** `{str(db_err)}`"
                    )

                # Formulate final response with data context
                answer_system_prompt = (
                    "Bạn là Kế toán trưởng & Chuyên gia tư vấn thuế chuyên nghiệp (Senior Tax Compliance Consultant) của meInvoice Intelligence.\n"
                    "Dưới đây là câu hỏi của người dùng, truy vấn SQL đã chạy và kết quả dữ liệu thực tế thu được từ cơ sở dữ liệu.\n"
                    "Nhiệm vụ của bạn là tổng hợp dữ liệu này và trả lời người dùng bằng tiếng Việt tự nhiên, chính xác, lịch sự.\n"
                    "Hãy luôn trả lời bằng giọng điệu chuyên nghiệp, chuẩn mực của một cố vấn thuế cấp cao. Trích dẫn chính xác các Điều, Khoản, Thông tư, Nghị định liên quan (ví dụ: Nghị định 123/2020/NĐ-CP về hóa đơn, Nghị định 125/2020/NĐ-CP về xử phạt hành chính thuế/hóa đơn, Thông tư 219/2013/TT-BTC về thuế GTGT, Luật Thuế GTGT mới 48/2024/QH15 hoặc Luật số 149/2025/QH15) khi đưa ra lời khuyên pháp lý.\n"
                    "Hãy trình bày dữ liệu dạng bảng Markdown Table hoặc danh sách nếu có nhiều dòng.\n"
                    "Luôn bao gồm câu truy vấn SQL đã chạy trong câu trả lời để người dùng kiểm chứng dưới định dạng code block.\n"
                    "Hãy đưa ra nhận xét hoặc cảnh báo về các rủi ro tuân thủ (ví dụ: các hóa đơn từ doanh nghiệp có MST rủi ro cao, thanh toán tiền mặt vượt hạn mức, hoặc giá mua biến động quá mức) nếu phát hiện trong kết quả."
                )
                answer_user_content = (
                    f"Câu hỏi: {user_message}\n\n"
                    f"Truy vấn SQL thực thi:\n```sql\n{sql_query}\n```\n\n"
                    f"Giải thích truy vấn: {explanation}\n\n"
                    f"Dữ liệu thu được (JSON):\n{json.dumps(rows, ensure_ascii=False, indent=2)}"
                )
                final_answer = self._call_llm(settings, answer_system_prompt, answer_user_content, response_format_json=False)
                return final_answer

            except Exception as sql_err:
                logger.warning(f"SQL flow failed: {sql_err}. Falling back to standard LLM chat.")

        # RAG - Search and retrieve tax regulations if intent is general_query
        tax_rag_context = ""
        if intent == "general_query":
            tax_rag_context = get_tax_rag_context(user_message)

        # Retrieve local e-invoices context for standard RAG fallback
        try:
            invoices = Invoice.query.all()
            invoice_list = []
            for inv in invoices[:50]:
                invoice_list.append({
                    "id": inv.id,
                    "number": inv.number,
                    "date": inv.date,
                    "seller": inv.seller_name,
                    "buyer": inv.buyer_name,
                    "total": inv.total_amount,
                    "cancelled": inv.is_cancelled,
                    "payment_method": inv.payment_method
                })
        except Exception as e:
            logger.warning(f"Failed to fetch invoices context for chat assistant: {e}")
            invoice_list = []

        system_prompt = (
            "Bạn là Kế toán trưởng & Chuyên gia tư vấn thuế chuyên nghiệp (Senior Tax Compliance Consultant) của meInvoice Intelligence.\n"
            "Nhiệm vụ của bạn là hỗ trợ kế toán truy vấn, phân tích dữ liệu hóa đơn điện tử, đồng thời giải đáp các thắc mắc về luật thuế, chính sách kế toán, quy định hóa đơn tại Việt Nam.\n"
            "Hãy luôn trả lời bằng giọng điệu chuyên nghiệp, chuẩn mực của một cố vấn thuế cấp cao. Trích dẫn chính xác các Điều, Khoản, Thông tư, Nghị định liên quan (ví dụ: Nghị định 123/2020/NĐ-CP về hóa đơn, Nghị định 125/2020/NĐ-CP về xử phạt hành chính thuế/hóa đơn, Thông tư 219/2013/TT-BTC về thuế GTGT, Luật Thuế GTGT mới 48/2024/QH15 hoặc Luật số 149/2025/QH15) khi đưa ra lời khuyên pháp lý.\n\n"
        )
        if invoice_context:
            system_prompt += invoice_context

        if tax_rag_context:
            system_prompt += (
                "Dưới đây là các tài liệu quy định pháp luật thuế liên quan được truy xuất từ cơ sở dữ liệu luật thuế (RAG Context):\n"
                f"{tax_rag_context}\n\n"
                "Khi trả lời các câu hỏi về luật thuế, hãy:\n"
                "- Trích dẫn chính xác các Điều, Khoản, Thông tư, Nghị định liên quan.\n"
                "- Cung cấp giải thích rõ ràng, chuyên nghiệp và có chiều sâu bằng tiếng Việt.\n"
                "- Đưa ra các khuyến nghị hoặc hành động cụ thể để giảm thiểu rủi ro pháp lý cho doanh nghiệp.\n\n"
            )
            
        system_prompt += (
            "Dưới đây là danh sách hóa đơn hiện có trong cơ sở dữ liệu để bạn tham khảo nếu câu hỏi của người dùng có liên quan đến dữ liệu thực tế:\n"
            f"{json.dumps(invoice_list, ensure_ascii=False, indent=2)}\n\n"
            "Hãy trả lời bằng tiếng Việt tự nhiên, cực kỳ chuyên nghiệp, chính xác và có thể sử dụng định dạng bảng (Markdown Table) hoặc danh sách khi cần thiết.\n"
            "Nếu người dùng hỏi thông tin không có trong danh sách hoặc không liên quan đến hóa đơn thuế/kế toán doanh nghiệp, hãy phản hồi lịch sự rằng bạn chỉ hỗ trợ kiểm soát hóa đơn và tư vấn thuế doanh nghiệp."
        )

        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:
            llm_messages.append({"role": msg.role, "content": msg.content})
        llm_messages.append({"role": "user", "content": user_message})

        try:
            provider = settings.get("ai_provider", "ollama").lower()
            model_name = settings.get("ai_model_name", "gemma-4")
            api_key_cipher = settings.get("ai_api_key", "")
            api_key = decrypt_password(api_key_cipher) if api_key_cipher else ""

            if provider == "ollama":
                endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
                url = f"{endpoint}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": llm_messages,
                    "stream": False,
                    "options": {"temperature": 0.2}
                }
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", "")

            elif provider == "gemini":
                m_name = model_name if model_name else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                prompt_parts = [system_prompt, "\n\nLịch sử hội thoại:"]
                for msg in llm_messages[1:]:
                    role_label = "Kế toán" if msg["role"] == "user" else "Trợ lý AI"
                    prompt_parts.append(f"{role_label}: {msg['content']}")
                prompt_parts.append("Trợ lý AI:")
                payload = {
                    "contents": [{"parts": [{"text": "\n".join(prompt_parts)}]}],
                    "generationConfig": {"temperature": 0.2}
                }
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

            elif provider == "openai":
                m_name = model_name if model_name else "gpt-4o-mini"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": m_name,
                    "messages": llm_messages,
                    "temperature": 0.2
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return f"Cấu hình nhà cung cấp AI không hợp lệ: {provider}"
        except Exception as e:
            logger.error(f"Chat assistant LLM fallback failed ({provider}): {e}")
            return f"Không thể kết nối tới mô hình AI ({provider}): {str(e)}."


class AIExpenseClassifier:
    """Classifies invoice line items into standard expense categories using LLMs or local fallbacks."""

    CATEGORIES = [
        "Văn phòng phẩm & Thiết bị văn phòng",
        "Thiết bị công nghệ & Phần mềm",
        "Chi phí tiếp khách & Hội nghị",
        "Quảng cáo, Tiếp thị & Sự kiện",
        "Vận chuyển, Giao hàng & Logistics",
        "Chi phí dịch vụ công cộng & Tiện ích",
        "Sửa chữa, Bảo trì & Nâng cấp",
        "Chi phí khác & Vật tư dùng chung"
    ]

    def classify_item_fallback(self, item_name: str) -> str:
        """Classify item name based on semantic keywords."""
        name_lower = item_name.lower()
        
        # Category 1: Văn phòng phẩm & Thiết bị văn phòng
        vpp_keywords = ["giấy", "giay", "bút", "but", "mực", "muc", "sổ", "so tay", "kẹp", "kep", "băng keo", "bang keo", "ghim", "kéo", "keo", "phong bì", "phong bi", "văn phòng phẩm", "van phong pham", "sách", "sach", "tập", "tap", "vở", "vo"]
        for kw in vpp_keywords:
            if kw in name_lower:
                return "Văn phòng phẩm & Thiết bị văn phòng"
                
        # Category 2: Thiết bị công nghệ & Phần mềm
        tech_keywords = ["máy tính", "may tinh", "laptop", "pc", "chuột", "chuot", "bàn phím", "ban phim", "màn hình", "man hinh", "ổ cứng", "o cung", "ssd", "ram", "phần mềm", "phan mem", "license", "cloud", "hosting", "server", "domain", "tên miền", "ten mien", "tai nghe", "camera", "máy ảnh", "may anh", "ipad", "điện thoại", "dien thoai", "iphone"]
        for kw in tech_keywords:
            if kw in name_lower:
                return "Thiết bị công nghệ & Phần mềm"
                
        # Category 3: Chi phí tiếp khách & Hội nghị
        meeting_keywords = ["ăn uống", "an uong", "ăn trưa", "an trua", "ăn tối", "an toi", "nhà hàng", "nha hang", "tiếp khách", "tiep khach", "tiếp đối tác", "tiep doi tac", "cà phê", "cafe", "coffee", "nước uống", "nuoc uong", "bia", "rượu", "ruou", "hội nghị", "hoi nghi", "phòng họp", "phong hop", "tiệc", "tiec", "buffet"]
        for kw in meeting_keywords:
            if kw in name_lower:
                return "Chi phí tiếp khách & Hội nghị"
                
        # Category 4: Quảng cáo, Tiếp thị & Sự kiện
        marketing_keywords = ["quảng cáo", "quang cao", "ads", "facebook", "google", "tiếp thị", "marketing", "sự kiện", "su kien", "event", "tờ rơi", "to roi", "banner", "standee", "in ấn tờ rơi", "in an to roi", "quà tặng", "qua tang", "triển lãm", "trien lam"]
        for kw in marketing_keywords:
            if kw in name_lower:
                return "Quảng cáo, Tiếp thị & Sự kiện"
                
        # Category 5: Vận chuyển, Giao hàng & Logistics
        shipping_keywords = ["vận chuyển", "van chuyen", "giao hàng", "giao hang", "ship", "chuyển phát", "chuyen phat", "logistics", "bưu điện", "buu dien", "cước xe", "cuoc xe", "phí vận chuyển", "phi van chuyen", "xe khách", "xe khach", "taxi", "grab"]
        for kw in shipping_keywords:
            if kw in name_lower:
                return "Vận chuyển, Giao hàng & Logistics"
                
        # Category 6: Chi phí dịch vụ công cộng & Tiện ích
        utility_keywords = ["điện", "dien", "nước", "nuoc", "internet", "wifi", "cáp", "cap", "thuê bao", "thue bao", "cước thuê bao", "cuoc thue bao", "thẻ cào", "the cao"]
        for kw in utility_keywords:
            if kw in name_lower:
                return "Chi phí dịch vụ công cộng & Tiện ích"
                
        # Category 7: Sửa chữa, Bảo trì & Nâng cấp
        repair_keywords = ["sửa chữa", "sua chua", "bảo trì", "bao tri", "vệ sinh máy", "ve sinh may", "thay thế linh kiện", "thay the linh kien", "nâng cấp", "nang cap", "bảo dưỡng", "bao duong", "sơn", "son", "quét vôi"]
        for kw in repair_keywords:
            if kw in name_lower:
                return "Sửa chữa, Bảo trì & Nâng cấp"
                
        return "Chi phí khác & Vật tư dùng chung"

    def classify_line_items(self, line_items: list[LineItem]) -> dict[int, str]:
        """Classify multiple LineItems using LLM or local keyword fallback."""
        if not line_items:
            return {}

        settings = load_scheduler_settings()
        
        # Check if AI/LLM classification is enabled in config
        if not settings.get("ai_enabled"):
            logger.info("AI classification is disabled. Using keyword fallback.")
            return {item.id: self.classify_item_fallback(item.item_name) for item in line_items}

        provider = settings.get("ai_provider", "ollama").lower()
        model_name = settings.get("ai_model_name", "gemma-4")
        api_key_cipher = settings.get("ai_api_key", "")
        api_key = decrypt_password(api_key_cipher) if api_key_cipher else ""

        # Prepare payload for LLM
        prompt_items = [{"id": item.id, "name": item.item_name} for item in line_items]

        system_prompt = (
            "Bạn là trợ lý kế toán chuyên nghiệp. Hãy phân loại danh sách mặt hàng hóa đơn mua sắm thành 1 trong 8 nhóm chi phí tiêu chuẩn sau:\n"
            "1. 'Văn phòng phẩm & Thiết bị văn phòng'\n"
            "2. 'Thiết bị công nghệ & Phần mềm'\n"
            "3. 'Chi phí tiếp khách & Hội nghị'\n"
            "4. 'Quảng cáo, Tiếp thị & Sự kiện'\n"
            "5. 'Vận chuyển, Giao hàng & Logistics'\n"
            "6. 'Chi phí dịch vụ công cộng & Tiện ích'\n"
            "7. 'Sửa chữa, Bảo trì & Nâng cấp'\n"
            "8. 'Chi phí khác & Vật tư dùng chung'\n\n"
            "Hãy phân tích tên mặt hàng kỹ lưỡng. Ví dụ: 'giấy double a' -> nhóm 1; 'chuột logitech' -> nhóm 2; 'grab giao hàng' -> nhóm 5.\n"
            "Trả về kết quả dưới dạng đối tượng JSON thuần túy có định dạng:\n"
            "{\n  \"classifications\": [\n    {\n      \"id\": <id mặt hàng>,\n      \"category\": \"Tên nhóm chi phí chính xác\"\n    }\n  ]\n}"
        )

        user_content = f"Danh sách mặt hàng cần phân loại:\n{json.dumps(prompt_items, ensure_ascii=False, indent=2)}"

        response_text = ""
        try:
            if provider == "ollama":
                endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
                url = f"{endpoint}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.05},
                    "format": "json"
                }
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("message", {}).get("content", "")

            elif provider == "gemini":
                m_name = model_name if model_name else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": f"{system_prompt}\n\n{user_content}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.05
                    }
                }
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

            elif provider == "openai":
                m_name = model_name if model_name else "gpt-4o-mini"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": m_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.05
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}. Falling back to keywords.")
            return {item.id: self.classify_item_fallback(item.item_name) for item in line_items}

        # Parse response mapping
        results = {}
        if response_text:
            try:
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

                parsed = json.loads(cleaned_text)
                classifications = parsed.get("classifications", [])
                for cls in classifications:
                    item_id = cls.get("id")
                    category = cls.get("category")
                    if item_id and category in self.CATEGORIES:
                        results[int(item_id)] = category
            except Exception as e:
                logger.error(f"Failed to parse classification response: {e}. Response was: {response_text}")

        # Complete missing classifications using fallback
        for item in line_items:
            if item.id not in results:
                results[item.id] = self.classify_item_fallback(item.item_name)

        return results


def spell_money_vietnamese(amount: float) -> str:
    """Spells a float amount into standard Vietnamese text.
    Example: 1500200 -> "Một triệu năm trăm nghìn hai trăm đồng chẵn"
    """
    try:
        amount_int = int(round(amount))
        if amount_int == 0:
            return "Không đồng"
        
        words = []
        units = ["", "nghìn", "triệu", "tỷ"]
        
        num_str = str(amount_int)
        pad_len = (3 - len(num_str) % 3) % 3
        num_str = "0" * pad_len + num_str
        
        groups = [num_str[i:i+3] for i in range(0, len(num_str), 3)]
        groups.reverse()
        
        digits_map = {
            '0': 'không', '1': 'một', '2': 'hai', '3': 'ba', '4': 'bốn',
            '5': 'năm', '6': 'sáu', '7': 'bảy', '8': 'tám', '9': 'chín'
        }
        
        def read_three_digits(g: str, is_highest: bool) -> list[str]:
            h, t, u = g[0], g[1], g[2]
            res = []
            
            if h != '0' or not is_highest:
                res.append(digits_map[h])
                res.append("trăm")
            
            if t == '0':
                if u != '0' and (h != '0' or not is_highest):
                    res.append("linh")
            elif t == '1':
                res.append("mười")
            else:
                res.append(digits_map[t])
                res.append("mươi")
            
            if u != '0':
                if u == '1' and t != '0' and t != '1':
                    res.append("mốt")
                elif u == '5' and t != '0':
                    res.append("lăm")
                elif u == '4' and t != '0' and t != '1':
                    res.append("tư")
                else:
                    res.append(digits_map[u])
            return res

        group_words = []
        for idx, g in enumerate(groups):
            if g == "000":
                continue
            
            is_highest = (idx == len(groups) - 1)
            g_w = read_three_digits(g, is_highest)
            
            scale_idx = idx % 3
            scale_word = units[scale_idx]
            
            billion_count = idx // 3
            suffix = []
            if scale_word:
                suffix.append(scale_word)
            for _ in range(billion_count):
                if scale_idx == 0:
                    pass
                else:
                    suffix.append("tỷ")
            if idx > 0 and idx % 3 == 0:
                suffix = ["tỷ"] * (idx // 3)
            
            g_w.extend(suffix)
            group_words.insert(0, " ".join(g_w))
            
        text = " ".join(group_words)
        text = " ".join(text.split())
        
        if text:
            text = text[0].upper() + text[1:] + " đồng chẵn"
        return text
    except Exception:
        return ""


def expand_abbreviations(text: str) -> str:
    """Expand common Vietnamese corporate and address abbreviations."""
    if not text:
        return ""
    
    corp_map = {
        r"\bTNHH\b": "Trách nhiệm Hữu hạn",
        r"\bCP\b": "Cổ phần",
        r"\bMTV\b": "Một thành viên",
        r"\bTM\b": "Thương mại",
        r"\bDV\b": "Dịch vụ",
        r"\bXNK\b": "Xuất nhập khẩu",
        r"\bCN\b": "Chi nhánh",
        r"\bMTR\b": "Môi trường",
        r"\bXD\b": "Xây dựng",
        r"\bĐT\b": "Đầu tư",
        r"\bPT\b": "Phát triển",
        r"\bSX\b": "Sản xuất",
        r"\bVT\b": "Vật tư",
        r"\bHC\b": "Hóa chất",
    }
    
    addr_map = {
        r"\bHN\b": "Hà Nội",
        r"\bHCM\b": "TP. Hồ Chí Minh",
        r"\bTP\.?HCM\b": "TP. Hồ Chí Minh",
        r"\bHP\b": "Hải Phòng",
        r"\bĐN\b": "Đà Nẵng",
        r"\bTX\b": "Thị xã",
        r"\bTP\b": "Thành phố",
        r"\bQ\.": "Quận ",
        r"\bH\.": "Huyện ",
        r"\bP\.": "Phường ",
        r"\bT\.": "Tỉnh ",
        r"\bHBT\b": "Hai Bà Trưng",
        r"\bCG\b": "Cầu Giấy",
        r"\bĐĐ\b": "Đống Đa",
        r"\bTH\b": "Thanh Xuân",
        r"\bBD\b": "Bình Dương",
        r"\bDN\b": "Đồng Nai",
    }
    
    import re
    res = text
    for pattern, repl in corp_map.items():
        res = re.sub(pattern, repl, res, flags=re.IGNORECASE)
    for pattern, repl in addr_map.items():
        res = re.sub(pattern, repl, res, flags=re.IGNORECASE)
        
    res = " ".join(res.split())
    return res


class AIDataRepairer:
    """Intelligent invoice metadata repair using local LLMs (Gemma-4) or fallbacks."""

    def repair_metadata(self, invoice) -> dict:
        settings = load_scheduler_settings()
        ai_enabled = settings.get("ai_enabled", False)
        
        fallback_seller_name = expand_abbreviations(invoice.seller_name)
        fallback_buyer_name = expand_abbreviations(invoice.buyer_name)
        fallback_buyer_address = expand_abbreviations(invoice.buyer_address)
        fallback_spelling = spell_money_vietnamese(invoice.total_amount)
        
        fallback_data = {
            "seller_name": fallback_seller_name,
            "buyer_name": fallback_buyer_name,
            "buyer_address": fallback_buyer_address,
            "amount_in_words": fallback_spelling
        }
        
        if not ai_enabled:
            return fallback_data

        system_prompt = (
            "Bạn là trợ lý AI chuyên nghiệp tối ưu hóa dữ liệu hóa đơn thuế Việt Nam.\n"
            "Hãy chuẩn hóa tên công ty, địa chỉ viết tắt và số tiền viết bằng chữ sang dạng đầy đủ và chuẩn xác nhất.\n"
            "Chỉ trả về dữ liệu định dạng JSON hợp lệ, khớp chính xác theo mẫu:\n"
            "{\n"
            "  \"seller_name\": \"...\",\n"
            "  \"buyer_name\": \"...\",\n"
            "  \"buyer_address\": \"...\",\n"
            "  \"amount_in_words\": \"...\"\n"
            "}\n"
            "Không kèm theo bất kỳ văn bản giải thích nào khác."
        )

        user_content = (
            f"Hãy tối ưu hóa dữ liệu hóa đơn sau:\n"
            f"- Tên người bán: {invoice.seller_name}\n"
            f"- Tên người mua: {invoice.buyer_name}\n"
            f"- Địa chỉ người mua: {invoice.buyer_address}\n"
            f"- Tổng tiền thanh toán: {invoice.total_amount}\n"
        )

        provider = settings.get("ai_provider", "ollama").lower()
        model_name = settings.get("ai_model_name", "gemma-4")
        api_key_cipher = settings.get("ai_api_key", "")
        api_key = decrypt_password(api_key_cipher) if api_key_cipher else ""

        response_text = ""
        try:
            if provider == "ollama":
                endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
                url = f"{endpoint}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.05}
                }
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("message", {}).get("content", "")

            elif provider == "gemini":
                m_name = model_name if model_name else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                prompt = f"{system_prompt}\n\n{user_content}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.05}
                }
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                response_text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        except Exception as e:
            logger.warning(f"AI metadata repair failed: {e}. Falling back.")
            return fallback_data

        if response_text:
            try:
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

                parsed = json.loads(cleaned_text)
                return {
                    "seller_name": parsed.get("seller_name") or fallback_seller_name,
                    "buyer_name": parsed.get("buyer_name") or fallback_buyer_name,
                    "buyer_address": parsed.get("buyer_address") or fallback_buyer_address,
                    "amount_in_words": parsed.get("amount_in_words") or fallback_spelling
                }
            except Exception as e:
                logger.error(f"Failed to parse AI repair JSON response: {e}. Response was: {response_text}")
                return fallback_data

        return fallback_data
