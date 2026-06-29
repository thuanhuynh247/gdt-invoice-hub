# -*- coding: utf-8 -*-
import os
import sqlite3
import requests
import json
import re
from datetime import datetime

try:
    from auth.crypto import decrypt_password, encrypt_password
except ImportError:
    def decrypt_password(ciphertext):
        return ciphertext
    def encrypt_password(password):
        return password

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.db")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH)

def load_settings():
    conn = get_db_connection()
    if not conn:
        return {}
    
    settings = {
        "ai_enabled": True,
        "ai_provider": "ollama",
        "ai_model_name": "gemma-4",
        "ai_api_key": "",
        "ai_ollama_endpoint": "http://localhost:11434"
    }
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'")
        if cursor.fetchone():
            cursor.execute("SELECT key, value FROM system_config")
            for row in cursor.fetchall():
                key, val = row
                if key in settings:
                    if val.lower() == "true":
                        settings[key] = True
                    elif val.lower() == "false":
                        settings[key] = False
                    else:
                        settings[key] = val
    except Exception:
        pass
    finally:
        conn.close()
        
    return settings

def save_settings(settings):
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        for k, v in settings.items():
            val_str = "true" if v is True else ("false" if v is False else str(v))
            cursor.execute("""
                INSERT INTO system_config (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (k, val_str))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_specialized_agent(query: str, forced_agent: str = None) -> tuple[str, str]:
    """Classify user query and return specialized agent name and system prompt instructions."""
    if forced_agent:
        fa = forced_agent.lower()
        if "tp" in fa or "transfer pricing" in fa or "auditor" in fa or "giao dịch liên kết" in fa:
            return "Chuyên gia Giao dịch liên kết (Transfer Pricing Auditor)", (
                "Bạn là Chuyên gia Giao dịch liên kết (Transfer Pricing Auditor) cao cấp của meInvoice Intelligence.\n"
                "Tập trung sâu vào: các quy định xác định giá giao dịch liên kết theo Nghị định 132/2020/NĐ-CP, tỷ lệ chi phí lãi vay được trừ (trần 30% EBITDA), nghĩa vụ kê khai mẫu biểu giao dịch liên kết (Mẫu 01, 02, 03, 04), nguyên tắc giao dịch độc lập (arm's length principle), và các rủi ro thanh tra chuyển giá của cơ quan thuế."
            )
        elif "pen" in fa or "penalties" in fa or "xử phạt" in fa or "phạt" in fa:
            return "Chuyên gia Xử phạt hành chính Thuế (Tax Penalties Specialist)", (
                "Bạn là Chuyên gia Xử phạt hành chính Thuế (Tax Penalties Specialist) cao cấp của meInvoice Intelligence.\n"
                "Tập trung sâu vào: các mức xử phạt hành chính về thuế và hóa đơn theo Nghị định 125/2020/NĐ-CP. Hướng dẫn các hành vi vi phạm thời hạn nộp hồ sơ khai thuế, lập hóa đơn sai thời điểm, chậm nộp thuế (tính tiền chậm nộp 0.03%/ngày), và các tình tiết giảm nhẹ hoặc miễn xử phạt hành chính thuế."
            )
        elif "fct" in fa or "contractor" in fa or "nhà thầu" in fa:
            return "Chuyên gia Thuế Nhà Thầu Nước Ngoài (FCT Consultant)", (
                "Bạn là Chuyên gia Thuế Nhà Thầu Nước Ngoài (FCT Consultant) cao cấp của meInvoice Intelligence.\n"
                "Tập trung sâu vào: đối tượng chịu thuế và không chịu thuế nhà thầu, phương pháp tính thuế nhà thầu (trực tiếp, khấu trừ, hỗn hợp) theo Thông tư 103/2014/TT-BTC. Trích dẫn tỷ lệ phần trăm thuế GTGT và thuế TNDN tính trên doanh thu tính thuế đối với từng hoạt động dịch vụ thương mại cụ thể của nhà thầu nước ngoài."
            )
        elif "vat" in fa or "gtgt" in fa or "giá trị gia tăng" in fa:
            return "Chuyên gia Thuế GTGT (VAT Consultant)", (
                "Bạn là Chuyên gia Thuế GTGT (VAT Consultant) cao cấp.\n"
                "Tập trung sâu vào: điều kiện khấu trừ thuế GTGT đầu vào, thủ tục hoàn thuế GTGT, các trường hợp chịu thuế suất 0%, 5%, 8%, 10%, KKKNT (không phải kê khai tính thuế), KCT (không chịu thuế), và các quy định mới nhất theo Luật Thuế GTGT số 48/2024/QH15 hoặc Luật số 149/2025/QH15.\n"
                "Hãy hướng dẫn chi tiết cách kê khai bổ sung thuế GTGT và xử lý các lỗi thường gặp."
            )
        elif "cit" in fa or "tndn" in fa or "thu nhập doanh nghiệp" in fa:
            return "Chuyên gia Thuế TNDN (CIT Consultant)", (
                "Bạn là Chuyên gia Thuế TNDN (CIT Consultant) cao cấp.\n"
                "Tập trung sâu vào: chi phí được trừ và không được trừ khi xác định thu nhập chịu thuế TNDN, ưu đãi thuế CIT, miễn giảm thuế, trích lập các quỹ, chuyển lỗ, các điều kiện về chứng từ không dùng tiền mặt đối với giao dịch từ 20 triệu VND trở lên, và các quy định theo Luật Thuế Thu nhập doanh nghiệp."
            )
        elif "pit" in fa or "tncn" in fa or "thu nhập cá nhân" in fa:
            return "Chuyên gia Thuế TNCN (PIT Consultant)", (
                "Bạn là Chuyên gia Thuế TNCN (PIT Consultant) cao cấp.\n"
                "Tập trung sâu vào: xác định đối tượng nộp thuế cư trú và không cư trú, các khoản thu nhập chịu thuế và được miễn thuế TNCN, mức giảm trừ gia cảnh cho bản thân và người phụ thuộc, cách tính thuế theo biểu thuế lũy tiến từng phần, và quyết toán thuế TNCN cuối năm cho người lao động."
            )
        elif "inv" in fa or "invoice" in fa or "hóa đơn" in fa or "chứng từ" in fa:
            return "Chuyên gia Hóa đơn & Chứng từ (Invoice Specialist)", (
                "Bạn là Chuyên gia Hóa đơn & Chứng từ (Invoice Specialist) cao cấp.\n"
                "Tập trung sâu vào: quy định lập, quản lý và sử dụng hóa đơn điện tử theo Nghị định 123/2020/NĐ-CP and Thông tư 78/2021/TT-BTC. Hướng dẫn chi tiết cách xử lý hóa đơn sai sót (điều chỉnh, thay thế, hủy, giải trình Mẫu 04/SS-HĐĐT), kiểm tra tính hợp lệ của chữ ký số (nky), mã cơ quan thuế (mccqt), và thời hạn hóa đơn."
            )
        elif "gen" in fa or "general" in fa or "tổng hợp" in fa:
            return "Cố vấn Thuế Tổng hợp (General Tax Advisor)", (
                "Bạn là Cố vấn Thuế Tổng hợp (General Tax Advisor) cao cấp.\n"
                "Tập trung giải đáp các vấn đề thuế tích hợp, mối liên quan giữa hóa đơn chứng từ, thuế GTGT, TNDN và kế toán tài chính doanh nghiệp."
            )

    q = query.lower()
    
    # 1. VAT (Value Added Tax)
    vat_keywords = ["gtgt", "giá trị gia tăng", "khấu trừ", "hoàn thuế", "vat", "suất", "8%", "10%", "đầu vào", "đầu ra"]
    # 2. CIT (Corporate Income Tax)
    cit_keywords = ["tndn", "thu nhập doanh nghiệp", "chi phí được trừ", "chi phí hợp lý", "miễn thuế", "cit", "lỗ", "kết chuyển"]
    # 3. PIT (Personal Income Tax)
    pit_keywords = ["tncn", "thu nhập cá nhân", "giảm trừ gia cảnh", "lương", "pit", "nhân sự", "lao động", "hợp đồng"]
    # 4. Invoicing & Documents
    inv_keywords = ["hóa đơn", "biên bản", "sai sót", "điều chỉnh", "thay thế", "hủy hóa đơn", "ký hiệu", "mẫu số", "nghị định 123", "thông tư 78", "nky", "tthai", "mccqt"]
    # 5. Transfer Pricing
    tp_keywords = ["liên kết", "chuyển giá", "132/2020", "chỉ số giao dịch", "báo cáo lợi nhuận", "liên kết kinh doanh", "arm's length", "arms length"]
    # 6. Tax Penalties
    pen_keywords = ["xử phạt", "phạt hành chính", "vi phạm", "nộp chậm", "trễ hạn", "125/2020", "tiền phạt", "mức phạt", "phạt tiền", "chậm nộp"]
    # 7. Foreign Contractor Tax (FCT)
    fct_keywords = ["nhà thầu nước ngoài", "nhà thầu phụ", "fct", "103/2014", "circular 103", "nhà thầu ngoại", "thuế nhà thầu"]

    if any(k in q for k in tp_keywords):
        agent_name = "Chuyên gia Giao dịch liên kết (Transfer Pricing Auditor)"
        instructions = (
            "Bạn là Chuyên gia Giao dịch liên kết (Transfer Pricing Auditor) cao cấp của meInvoice Intelligence.\n"
            "Tập trung sâu vào: các quy định xác định giá giao dịch liên kết theo Nghị định 132/2020/NĐ-CP, tỷ lệ chi phí lãi vay được trừ (trần 30% EBITDA), nghĩa vụ kê khai mẫu biểu giao dịch liên kết (Mẫu 01, 02, 03, 04), nguyên tắc giao dịch độc lập (arm's length principle), và các rủi ro thanh tra chuyển giá của cơ quan thuế."
        )
    elif any(k in q for k in pen_keywords):
        agent_name = "Chuyên gia Xử phạt hành chính Thuế (Tax Penalties Specialist)"
        instructions = (
            "Bạn là Chuyên gia Xử phạt hành chính Thuế (Tax Penalties Specialist) cao cấp của meInvoice Intelligence.\n"
            "Tập trung sâu vào: các mức xử phạt hành chính về thuế và hóa đơn theo Nghị định 125/2020/NĐ-CP. Hướng dẫn các hành vi vi phạm thời hạn nộp hồ sơ khai thuế, lập hóa đơn sai thời điểm, chậm nộp thuế (tính tiền chậm nộp 0.03%/ngày), và các tình tiết giảm nhẹ hoặc miễn xử phạt hành chính thuế."
        )
    elif any(k in q for k in fct_keywords):
        agent_name = "Chuyên gia Thuế Nhà Thầu Nước Ngoài (FCT Consultant)"
        instructions = (
            "Bạn là Chuyên gia Thuế Nhà Thầu Nước Ngoài (FCT Consultant) cao cấp của meInvoice Intelligence.\n"
            "Tập trung sâu vào: đối tượng chịu thuế và không chịu thuế nhà thầu, phương pháp tính thuế nhà thầu (trực tiếp, khấu trừ, hỗn hợp) theo Thông tư 103/2014/TT-BTC. Trích dẫn tỷ lệ phần trăm thuế GTGT và thuế TNDN tính trên doanh thu tính thuế đối với từng hoạt động dịch vụ thương mại cụ thể của nhà thầu nước ngoài."
        )
    elif any(k in q for k in vat_keywords):
        agent_name = "Chuyên gia Thuế GTGT (VAT Consultant)"
        instructions = (
            "Bạn là Chuyên gia Thuế GTGT (VAT Consultant) cao cấp.\n"
            "Tập trung sâu vào: điều kiện khấu trừ thuế GTGT đầu vào, thủ tục hoàn thuế GTGT, các trường hợp chịu thuế suất 0%, 5%, 8%, 10%, KKKNT (không phải kê khai tính thuế), KCT (không chịu thuế), và các quy định mới nhất theo Luật Thuế GTGT số 48/2024/QH15 hoặc Luật số 149/2025/QH15.\n"
            "Hãy hướng dẫn chi tiết cách kê khai bổ sung thuế GTGT và xử lý các lỗi thường gặp."
        )
    elif any(k in q for k in cit_keywords):
        agent_name = "Chuyên gia Thuế TNDN (CIT Consultant)"
        instructions = (
            "Bạn là Chuyên gia Thuế TNDN (CIT Consultant) cao cấp.\n"
            "Tập trung sâu vào: chi phí được trừ và không được trừ khi xác định thu nhập chịu thuế TNDN, ưu đãi thuế CIT, miễn giảm thuế, trích lập các quỹ, chuyển lỗ, các điều kiện về chứng từ không dùng tiền mặt đối với giao dịch từ 20 triệu VND trở lên, và các quy định theo Luật Thuế Thu nhập doanh nghiệp."
        )
    elif any(k in q for k in pit_keywords):
        agent_name = "Chuyên gia Thuế TNCN (PIT Consultant)"
        instructions = (
            "Bạn là Chuyên gia Thuế TNCN (PIT Consultant) cao cấp.\n"
            "Tập trung sâu vào: xác định đối tượng nộp thuế cư trú và không cư trú, các khoản thu nhập chịu thuế và được miễn thuế TNCN, mức giảm trừ gia cảnh cho bản thân và người phụ thuộc, cách tính thuế theo biểu thuế lũy tiến từng phần, và quyết toán thuế TNCN cuối năm cho người lao động."
        )
    elif any(k in q for k in inv_keywords) or not q:
        agent_name = "Chuyên gia Hóa đơn & Chứng từ (Invoice Specialist)"
        instructions = (
            "Bạn là Chuyên gia Hóa đơn & Chứng từ (Invoice Specialist) cao cấp.\n"
            "Tập trung sâu vào: quy định lập, quản lý và sử dụng hóa đơn điện tử theo Nghị định 123/2020/NĐ-CP và Thông tư 78/2021/TT-BTC. Hướng dẫn chi tiết cách xử lý hóa đơn sai sót (điều chỉnh, thay thế, hủy, giải trình Mẫu 04/SS-HĐĐT), kiểm tra tính hợp lệ của chữ ký số (nky), mã cơ quan thuế (mccqt), và thời hạn hóa đơn."
        )
    else:
        # General Tax Agent
        agent_name = "Cố vấn Thuế Tổng hợp (General Tax Advisor)"
        instructions = (
            "Bạn là Cố vấn Thuế Tổng hợp (General Tax Advisor) cao cấp.\n"
            "Tập trung giải đáp các vấn đề thuế tích hợp, mối liên quan giữa hóa đơn chứng từ, thuế GTGT, TNDN và kế toán tài chính doanh nghiệp."
        )
        
    return agent_name, instructions


def get_rag_context(query: str):
    conn = get_db_connection()
    if not conn:
        return "", []
    
    try:
        clean_q = re.sub(r'[^\w\s\d]', ' ', query).strip()
        if not clean_q:
            clean_q = query
            
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tax_regulation_fts'")
        if not cursor.fetchone():
            return "", []
            
        # Try direct FTS5 MATCH first
        sql = """
            SELECT chunk_content, document_source, page_number
            FROM tax_regulation_fts
            WHERE tax_regulation_fts MATCH ?
            ORDER BY bm25(tax_regulation_fts) ASC
            LIMIT 3;
        """
        cursor.execute(sql, (clean_q,))
        res = cursor.fetchall()
        
        # Fallback 1: Tokenized OR fallback if 0 results
        if not res:
            tokens = [t.strip() for t in clean_q.split() if len(t.strip()) >= 2]
            if tokens:
                fallback_q = " OR ".join([f"{token}*" for token in tokens])
                cursor.execute(sql, (fallback_q,))
                res = cursor.fetchall()
                
        # Fallback 2: Simple LIKE on tax_regulation_chunk if still 0 results
        if not res:
            tokens = [t.strip() for t in clean_q.split() if len(t.strip()) >= 3]
            if tokens:
                tokens = sorted(tokens, key=len, reverse=True)[:3]
                like_clauses = " AND ".join(["chunk_content LIKE ?" for _ in tokens])
                like_sql = f"""
                    SELECT chunk_content, document_source, page_number
                    FROM tax_regulation_chunk
                    WHERE {like_clauses}
                    LIMIT 3;
                """
                like_params = [f"%{token}%" for token in tokens]
                cursor.execute(like_sql, like_params)
                res = cursor.fetchall()
        
        if res:
            matches = []
            citations = []
            for row in res:
                content, source, page = row
                matches.append(f"### [{source} - Trang {page}]\n{content}")
                
                # Check for corresponding rendered image page
                base_doc = os.path.splitext(source)[0]
                img_name = f"{base_doc}_page_{page}.png"
                workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                img_path = os.path.join(workspace_dir, "static", "tax_pages", img_name)
                
                if os.path.exists(img_path):
                    citations.append({
                        "source": source,
                        "page": page,
                        "img_path": img_path
                    })
            return "\n\n".join(matches), citations
    except Exception as e:
        print(f"Error in RAG: {e}")
    finally:
        conn.close()
    return "", []


def parse_amount_from_query(query: str) -> float | None:
    q = query.lower()
    
    # 1. Match patterns like 1.5 tỷ, 500tr, 500 triệu, 100.000.000, etc.
    match = re.search(r'(\d+(?:[\.,]\d+)?)\s*(tỷ|triệu|tr)\b', q)
    if match:
        val_str = match.group(1).replace(',', '.')
        try:
            val = float(val_str)
        except ValueError:
            return None
        unit = match.group(2)
        if 'tỷ' in unit:
            val *= 1_000_000_000
        elif 'triệu' in unit or 'tr' in unit:
            val *= 1_000_000
        return val
        
    # 2. Look for large numbers with thousand separators
    match_num = re.search(r'\b(\d{1,3}(?:[\.,]\d{3})+|\d{5,15})\b', q)
    if match_num:
        num_str = match_num.group(1)
        if '.' in num_str and ',' in num_str:
            if num_str.find('.') < num_str.find(','):
                num_str = num_str.replace('.', '').replace(',', '.')
            else:
                num_str = num_str.replace(',', '')
        elif '.' in num_str:
            parts = num_str.split('.')
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
                num_str = num_str.replace('.', '')
        elif ',' in num_str:
            parts = num_str.split(',')
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
                num_str = num_str.replace(',', '')
            else:
                num_str = num_str.replace(',', '.')
                
        try:
            return float(num_str)
        except ValueError:
            pass
            
    return None


def detect_and_run_tools(query: str) -> dict | None:
    """Detect if the query contains intent for FCT or tax penalty calculations.
    
    If detected, executes calculations and returns detailed data/HTML output.
    """
    q = query.lower()
    
    # 1. FCT calculation detection
    fct_triggers = ["tính thuế nhà thầu", "tính fct", "fct calculator", "thuế nhà thầu net", "thuế nhà thầu gross", "thuế nhà thầu"]
    if any(trigger in q for trigger in fct_triggers):
        val = parse_amount_from_query(query)
        has_defaulted_val = False
        if val is None:
            val = 100000000.0
            has_defaulted_val = True
            
        contract_type = "gross"
        if any(w in q for w in ["net", "chưa thuế", "không bao gồm", "chưa tính"]):
            contract_type = "net"
            
        industry_type = "services"
        if any(w in q for w in ["hàng hóa", "kèm dịch vụ", "lắp ráp", "lắp đặt"]):
            industry_type = "goods_with_services"
        elif any(w in q for w in ["xây dựng"]) and any(w in q for w in ["bao thầu", "có vật tư"]):
            industry_type = "construction_with_materials"
        elif any(w in q for w in ["xây dựng"]):
            industry_type = "construction_no_materials"
        elif any(w in q for w in ["vận tải", "vận chuyển"]):
            industry_type = "transport_other"
        elif any(w in q for w in ["bản quyền", "phần mềm", "royalty", "licence", "sở hữu trí tuệ"]):
            industry_type = "royalties"
        elif any(w in q for w in ["lãi vay", "tiền vay", "vay vốn"]):
            industry_type = "loan_interest"
        elif any(w in q for w in ["chứng khoán", "cổ phần", "chuyển nhượng vốn"]):
            industry_type = "securities_transfer"
            
        try:
            from invoices.tax_audit_service import calculate_fct_tax
        except ImportError:
            from tax_audit_service import calculate_fct_tax
            
        try:
            res = calculate_fct_tax(val, contract_type, industry_type)
            res["estimated_value"] = has_defaulted_val
            
            html_output = f"""
<div class="card border-success border-2 shadow-sm my-3 tool-calc-card" style="animation: fadeInUp 0.3s ease-in-out;">
  <div class="card-header bg-success text-white d-flex align-items-center justify-content-between py-2">
    <span class="fw-bold"><i class="bi bi-calculator-fill me-2"></i> meInvoice Intelligence: FCT Calculator Engine</span>
    <span class="badge bg-light text-success fw-semibold">Circular 103/2014/TT-BTC</span>
  </div>
  <div class="card-body bg-light text-dark p-3" style="font-size: 0.9rem;">
    {f'<div class="alert alert-warning py-1 px-2 mb-2" style="font-size: 0.8rem;"><i class="bi bi-info-circle-fill me-1"></i> Không tìm thấy số tiền cụ thể trong câu hỏi, hệ thống đang mô phỏng với mức <strong>100.000.000 VND</strong></div>' if has_defaulted_val else ''}
    <div class="row g-3">
      <div class="col-md-6 border-end">
        <p class="mb-1 text-muted">Giá trị hợp đồng đầu vào:</p>
        <h5 class="fw-bold text-success mb-2">{res['contract_value']:,.0f} VND ({res['contract_type'].upper()})</h5>
        <p class="mb-1 text-muted">Loại hình kinh doanh nhà thầu:</p>
        <span class="badge bg-secondary mb-3 text-wrap text-start">{res['industry_description']}</span>
        <div class="d-flex justify-content-between mb-1">
          <span>Thuế suất GTGT nhà thầu:</span>
          <strong class="text-success">{res['vat_rate'] * 100:.1f}%</strong>
        </div>
        <div class="d-flex justify-content-between">
          <span>Thuế suất TNDN nhà thầu:</span>
          <strong class="text-success">{res['cit_rate'] * 100:.1f}%</strong>
        </div>
      </div>
      <div class="col-md-6">
        <p class="mb-2 fw-semibold text-secondary">Kết quả phân bổ nghĩa vụ thuế:</p>
        <div class="d-flex justify-content-between mb-2 pb-1 border-bottom">
          <span>Doanh thu tính thuế GTGT:</span>
          <strong>{res['gross_revenue']:,.0f} VND</strong>
        </div>
        <div class="d-flex justify-content-between mb-2 pb-1 border-bottom">
          <span>Doanh thu tính thuế TNDN:</span>
          <strong>{res['cit_revenue']:,.0f} VND</strong>
        </div>
        <div class="d-flex justify-content-between text-danger fw-bold mb-2 pb-1 border-bottom">
          <span>1. Thuế GTGT phải nộp:</span>
          <span>{res['fct_vat']:,.0f} VND</span>
        </div>
        <div class="d-flex justify-content-between text-danger fw-bold mb-2 pb-1 border-bottom">
          <span>2. Thuế TNDN phải nộp:</span>
          <span>{res['fct_cit']:,.0f} VND</span>
        </div>
        <div class="d-flex justify-content-between text-success fw-bold py-1 bg-white px-2 rounded border border-success">
          <span>TỔNG THUẾ NHÀ THẦU (FCT):</span>
          <span>{res['total_fct']:,.0f} VND</span>
        </div>
      </div>
    </div>
    <div class="mt-3 pt-2 border-top text-muted" style="font-size: 0.75rem;">
      <i class="bi bi-book me-1"></i> <strong>Cơ sở pháp lý:</strong> {res['circular_reference']}
    </div>
  </div>
</div>
"""
            res["html_output"] = html_output
            res["tool_name"] = "FCT Calculator"
            return res
        except Exception as e:
            print(f"Error executing FCT tool: {e}")
            return None
            
    # 2. Tax penalty detection
    penalty_triggers = ["tính phạt chậm nộp", "tính phạt muộn", "phạt chậm nộp", "phạt kê khai", "tiền chậm nộp", "phạt thuế", "phạt trễ nộp"]
    if any(trigger in q for trigger in penalty_triggers):
        val = parse_amount_from_query(query)
        has_defaulted_val = False
        if val is None:
            val = 100000000.0
            has_defaulted_val = True
            
        match_days = re.search(r'(\d+)\s*ngày', q)
        has_defaulted_days = False
        if match_days:
            late_days = int(match_days.group(1))
        else:
            late_days = 30
            has_defaulted_days = True
            
        evasion_multiplier = 0.0
        if any(w in q for w in ["trốn thuế", "gian lận"]):
            evasion_multiplier = 1.0
            
        try:
            from invoices.tax_audit_service import calculate_audit_penalties
        except ImportError:
            from tax_audit_service import calculate_audit_penalties
            
        try:
            from datetime import date, timedelta
            due_date = date(2026, 1, 1)
            payment_date = due_date + timedelta(days=late_days)
            
            res = calculate_audit_penalties(val, due_date, payment_date, evasion_multiplier)
            res["estimated_value"] = has_defaulted_val
            res["estimated_days"] = has_defaulted_days
            
            html_output = f"""
<div class="card border-danger border-2 shadow-sm my-3 tool-calc-card" style="animation: fadeInUp 0.3s ease-in-out;">
  <div class="card-header bg-danger text-white d-flex align-items-center justify-content-between py-2">
    <span class="fw-bold"><i class="bi bi-exclamation-octagon-fill me-2"></i> meInvoice Intelligence: Tax Penalty Predictor</span>
    <span class="badge bg-light text-danger fw-semibold">Decree 125/2020/NĐ-CP</span>
  </div>
  <div class="card-body bg-light text-dark p-3" style="font-size: 0.9rem;">
    {f'<div class="alert alert-warning py-1 px-2 mb-2" style="font-size: 0.8rem;"><i class="bi bi-info-circle-fill me-1"></i> Thiếu thông tin số tiền hoặc số ngày. Đang giả lập với: <strong>{val:,.0f} VND</strong> và <strong>{late_days} ngày</strong> chậm nộp.</div>' if (has_defaulted_val or has_defaulted_days) else ''}
    <div class="row g-3">
      <div class="col-md-6 border-end">
        <p class="mb-1 text-muted">Số thuế khai thiếu/chậm nộp:</p>
        <h5 class="fw-bold text-danger mb-2">{res['underpaid_tax']:,.0f} VND</h5>
        <p class="mb-1 text-muted">Số ngày chậm nộp tờ khai/tiền thuế:</p>
        <h5 class="fw-bold text-dark mb-3">{res['late_days']} ngày</h5>
        <div class="d-flex justify-content-between mb-1">
          <span>Phạt chậm nộp tờ khai (20%):</span>
          <strong class="text-danger">{res['under_declaration_fine']:,.0f} VND</strong>
        </div>
        <div class="d-flex justify-content-between">
          <span>Tiền lãi chậm nộp (0.03%/ngày):</span>
          <strong class="text-danger">{res['late_interest']:,.0f} VND</strong>
        </div>
      </div>
      <div class="col-md-6">
        <p class="mb-2 fw-semibold text-secondary">Tổng nghĩa vụ thuế bổ sung:</p>
        <div class="d-flex justify-content-between mb-2 pb-1 border-bottom">
          <span>Số thuế gốc nộp bổ sung:</span>
          <strong>{res['underpaid_tax']:,.0f} VND</strong>
        </div>
        <div class="d-flex justify-content-between text-danger fw-bold mb-2 pb-1 border-bottom">
          <span>Tổng mức phạt xử phạt hành chính:</span>
          <span>{(res['under_declaration_fine'] + res['evasion_fine']):,.0f} VND</span>
        </div>
        <div class="d-flex justify-content-between text-danger fw-bold mb-2 pb-1 border-bottom">
          <span>Tiền lãi chậm nộp (0.03%/ngày):</span>
          <span>{res['late_interest']:,.0f} VND</span>
        </div>
        <div class="d-flex justify-content-between text-danger fw-bold mb-2 pb-1 border-bottom">
          <span>Tổng số tiền phạt phát sinh thêm:</span>
          <span>{res['total_penalties']:,.0f} VND</span>
        </div>
        <div class="d-flex justify-content-between text-danger fw-bold py-1 bg-white px-2 rounded border border-danger">
          <span>TỔNG SỐ PHẢI NỘP SAU PHẠT:</span>
          <span>{res['total_liability']:,.0f} VND</span>
        </div>
      </div>
    </div>
    <div class="mt-3 pt-2 border-top text-muted" style="font-size: 0.75rem;">
      <i class="bi bi-book me-1"></i> <strong>Cơ sở pháp lý:</strong> {res['decree_reference']}
    </div>
  </div>
</div>
"""
            res["html_output"] = html_output
            res["tool_name"] = "Tax Penalty Predictor"
            return res
        except Exception as e:
            print(f"Error executing Tax Penalty tool: {e}")
            return None

    # 3. PIT calculation detection
    pit_triggers = ["tính thuế tncn", "tính pit", "thuế tncn", "pit calculator"]
    if any(trigger in q for trigger in pit_triggers):
        val = parse_amount_from_query(query)
        has_defaulted_val = False
        if val is None:
            val = 30000000.0
            has_defaulted_val = True
            
        match_dep = re.search(r'(\d+)\s*(người phụ thuộc|người|phụ thuộc)', q)
        has_defaulted_dep = False
        if match_dep:
            dependents = int(match_dep.group(1))
        else:
            dependents = 0
            if "phụ thuộc" in q:
                dependents = 1
            else:
                has_defaulted_dep = True
                
        try:
            from invoices.tax_audit_service import calculate_pit_tax
        except ImportError:
            from tax_audit_service import calculate_pit_tax
            
        try:
            res = calculate_pit_tax(val, dependents)
            res["estimated_value"] = has_defaulted_val
            res["estimated_dep"] = has_defaulted_dep
            
            html_output = f"""
<div class="card border-primary border-2 shadow-sm my-3 tool-calc-card" style="animation: fadeInUp 0.3s ease-in-out;">
  <div class="card-header bg-primary text-white d-flex align-items-center justify-content-between py-2">
    <span class="fw-bold"><i class="bi bi-person-fill-check me-2"></i> meInvoice Intelligence: PIT Calculator Engine</span>
    <span class="badge bg-light text-primary fw-semibold">Resolution 954/2020/UBTVQH14</span>
  </div>
  <div class="card-body bg-light text-dark p-3" style="font-size: 0.9rem;">
    {f'<div class="alert alert-warning py-1 px-2 mb-2" style="font-size: 0.8rem;"><i class="bi bi-info-circle-fill me-1"></i> Không tìm thấy mức thu nhập hoặc người phụ thuộc. Đang giả lập với: <strong>{val:,.0f} VND</strong> thu nhập và <strong>{dependents} người phụ thuộc</strong>.</div>' if (has_defaulted_val) else ''}
    <div class="row g-3">
      <div class="col-md-6 border-end">
        <p class="mb-1 text-muted">Tổng thu nhập chịu thuế hàng tháng:</p>
        <h5 class="fw-bold text-primary mb-2">{res['monthly_income']:,.0f} VND</h5>
        <p class="mb-1 text-muted">Số người phụ thuộc kê khai:</p>
        <h5 class="fw-bold text-dark mb-3">{res['dependents']} người</h5>
        <div class="d-flex justify-content-between mb-1">
          <span>Giảm trừ bản thân:</span>
          <strong class="text-muted">{res['personal_deduction']:,.0f} VND</strong>
        </div>
        <div class="d-flex justify-content-between mb-1">
          <span>Giảm trừ người phụ thuộc:</span>
          <strong class="text-muted">{res['dependent_deduction']:,.0f} VND</strong>
        </div>
        <div class="d-flex justify-content-between pt-1 border-top fw-semibold text-secondary">
          <span>Tổng mức giảm trừ gia cảnh:</span>
          <span>{res['total_deductions']:,.0f} VND</span>
        </div>
      </div>
      <div class="col-md-6">
        <p class="mb-2 fw-semibold text-secondary">Kết quả tính thuế TNCN lũy tiến:</p>
        <div class="d-flex justify-content-between mb-2 pb-1 border-bottom">
          <span>Thu nhập tính thuế (sau giảm trừ):</span>
          <strong>{res['taxable_income']:,.0f} VND</strong>
        </div>
        <div class="d-flex justify-content-between mb-2 pb-1 border-bottom">
          <span>Bậc thuế lũy tiến cao nhất:</span>
          <span class="badge bg-primary">Bậc {res['active_tier']} ({res['tax_rate'] * 100:.0f}%)</span>
        </div>
        <div class="d-flex justify-content-between text-danger fw-bold mb-2 pb-1 border-bottom">
          <span>Thuế TNCN phải nộp:</span>
          <span>{res['pit_tax']:,.0f} VND</span>
        </div>
        <div class="d-flex justify-content-between text-success fw-bold py-1 bg-white px-2 rounded border border-primary">
          <span>THU NHẬP THỰC NHẬN (NET):</span>
          <span>{res['net_income']:,.0f} VND</span>
        </div>
      </div>
    </div>
    <div class="mt-3 pt-2 border-top text-muted" style="font-size: 0.75rem;">
      <i class="bi bi-book me-1"></i> <strong>Cơ sở pháp lý:</strong> {res['legal_reference']}
    </div>
  </div>
</div>
"""
            res["html_output"] = html_output
            res["tool_name"] = "PIT Calculator"
            return res
        except Exception as e:
            print(f"Error executing PIT tool: {e}")
            return None

    return None



def generate_dynamic_suggestions(query: str, context: str, agent_name: str) -> list[str]:
    """Generate 3 dynamic, context-aware Vietnamese follow-up suggestions."""
    q = query.lower()
    
    if "transfer pricing" in agent_name.lower() or "giao dịch liên kết" in q or "chuyển giá" in q:
        return [
            "Cách kê khai Mẫu 01 Giao dịch liên kết năm 2026",
            "Trần chi phí lãi vay EBITDA 30% áp dụng thế nào?",
            "Làm thế nào để lập hồ sơ xác định giá độc lập?"
        ]
    elif "fct" in agent_name.lower() or "nhà thầu" in q or "fct" in q:
        return [
            "Tính thuế nhà thầu Net dịch vụ 1 tỷ VND",
            "Thuế nhà thầu cho bản quyền phần mềm nước ngoài là bao nhiêu?",
            "Cách kê khai mẫu 01/NTNN thuế nhà thầu trực tuyến"
        ]
    elif "xử phạt" in agent_name.lower() or "penalties" in agent_name.lower() or "phạt" in q or "chậm nộp" in q:
        return [
            "Mức phạt lập hóa đơn điện tử sai thời điểm năm 2026",
            "Tính phạt chậm nộp 100 triệu VND thuế GTGT trễ 45 ngày",
            "Làm thư giải trình xin miễn giảm tiền phạt chậm nộp thế nào?"
        ]
    elif "gtgt" in agent_name.lower() or "vat" in q or "giá trị gia tăng" in q or "khấu trừ" in q:
        return [
            "Điều kiện để khấu trừ thuế GTGT đầu vào hóa đơn trên 20 triệu",
            "Thuế suất GTGT 8% có được tiếp tục áp dụng trong năm 2026?",
            "Hướng dẫn kê khai bổ sung điều chỉnh thuế GTGT đầu ra bị sót"
        ]
    elif "tndn" in agent_name.lower() or "cit" in q or "thu nhập doanh nghiệp" in q or "chi phí được trừ" in q:
        return [
            "Các chi phí không được trừ phổ biến khi quyết toán thuế TNDN",
            "Quy chế hoàn ứng thanh toán bằng thẻ cá nhân hợp lệ chi phí",
            "Thủ tục kết chuyển số lỗ thuế TNDN của năm trước"
        ]
    elif "tncn" in agent_name.lower() or "pit" in q or "thu nhập cá nhân" in q or "giảm trừ" in q:
        return [
            "Mức giảm trừ gia cảnh thuế TNCN mới nhất năm 2026",
            "Cách quyết toán thuế TNCN trực tuyến cho cá nhân tự làm",
            "Khấu trừ thuế TNCN 10% cho lao động thời vụ dưới 3 tháng"
        ]
    elif "hóa đơn" in agent_name.lower() or "invoice" in q:
        return [
            "Cách xử lý hóa đơn điện tử viết sai mã số thuế người mua",
            "Hóa đơn điện tử lập sai thời điểm có được khấu trừ thuế?",
            "Quy trình nộp mẫu 04/SS-HĐĐT giải trình hóa đơn sai sót"
        ]
    else:
        return [
            "Ủy quyền thanh toán thẻ cá nhân trên 20 triệu được khấu trừ thuế thế nào?",
            "Mức phạt muộn thời hạn nộp quyết toán thuế TNDN năm",
            "Tính thuế nhà thầu Net dịch vụ 500tr VND"
        ]

def call_llm(settings, system_prompt, user_content, history=None):
    provider = settings.get("ai_provider", "ollama").lower()
    model_name = settings.get("ai_model_name", "gemma-4")
    api_key_cipher = settings.get("ai_api_key", "")
    
    api_key = ""
    if api_key_cipher:
        try:
            api_key = decrypt_password(api_key_cipher)
        except Exception:
            api_key = api_key_cipher

    # If provider key is empty, attempt to resolve from environment variables
    if provider == "gemini" and not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    elif provider == "openai" and not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")

    # Auto-fallback check if Ollama endpoint is unreachable
    if provider == "ollama":
        endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
        try:
            # Short timeout to detect offline Ollama
            requests.get(endpoint, timeout=1.0)
        except requests.RequestException:
            # Ollama is offline. Try to fallback to Gemini first, then OpenAI
            gemini_env_key = os.environ.get("GEMINI_API_KEY")
            openai_env_key = os.environ.get("OPENAI_API_KEY")
            if gemini_env_key:
                provider = "gemini"
                model_name = "gemini-2.5-flash"
                api_key = gemini_env_key
                print("⚠️ Ollama offline. Auto-falling back to Gemini.")
            elif openai_env_key:
                provider = "openai"
                model_name = "gpt-4o-mini"
                api_key = openai_env_key
                print("⚠️ Ollama offline. Auto-falling back to OpenAI.")

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_content})

    if provider == "ollama":
        endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434").rstrip("/")
        url = f"{endpoint}/api/chat"
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1}
        }
        resp = requests.post(url, json=payload, timeout=45)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()

    elif provider == "gemini":
        m_name = model_name if model_name and "gemini" in model_name else "gemini-2.5-flash"
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
        resp = requests.post(url, json=payload, timeout=45)
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
        resp = requests.post(url, json=payload, headers=headers, timeout=45)
        resp.raise_for_status()
        return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    else:
        raise ValueError(f"Provider '{provider}' không được hỗ trợ.")


def translate_text(text: str, target_lang: str) -> str:
    """Translate tax/accounting text into English, Chinese, Japanese, or Korean using the configured LLM."""
    if not text or not text.strip():
        return ""
        
    settings = load_settings()
    if not settings.get("ai_enabled", True):
        return f"[AI Disabled] Mock Translation to {target_lang}: {text[:50]}..."
        
    # Map target language codes or names to standard Vietnamese display names for the prompt
    lang_map = {
        "en": "Tiếng Anh (English)",
        "zh": "Tiếng Trung (Chinese)",
        "ja": "Tiếng Nhật (Japanese)",
        "ko": "Tiếng Hàn (Korean)",
        "english": "Tiếng Anh (English)",
        "chinese": "Tiếng Trung (Chinese)",
        "japanese": "Tiếng Nhật (Japanese)",
        "korean": "Tiếng Hàn (Korean)"
    }
    
    lang_name = lang_map.get(target_lang.lower(), target_lang)
    
    system_prompt = (
        f"Bạn là một chuyên gia dịch thuật tài liệu tài chính, kế toán và luật thuế chuyên nghiệp.\n"
        f"Nhiệm vụ của bạn là dịch đoạn văn bản sau đây sang {lang_name}.\n"
        "Hãy giữ nguyên các thuật ngữ chuyên ngành kế toán, thuế (ví dụ: VAT/GTGT, CIT/TNDN, PIT/TNCN, hóa đơn điện tử, khấu trừ, chi phí hợp lý,...) một cách chuẩn xác nhất theo thông lệ quốc tế.\n"
        "Chỉ trả về bản dịch duy nhất, không thêm bất kỳ lời bình luận, giải thích hay ký tự dẫn nhập nào."
    )
    
    try:
        translated = call_llm(settings, system_prompt, text)
        return translated
    except Exception as e:
        # Fallback if LLM call fails (e.g. no internet or Ollama not running)
        return f"[Translation Error: {str(e)}] Bản dịch giả lập sang {lang_name} cho: {text[:100]}..."


def clean_and_parse_json(text):
    text = text.strip()
    if not text:
        return None
        
    # Strip markdown wrappers
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        
    try:
        return json.loads(text)
    except Exception:
        # Try finding JSON using regex
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return None


def call_llm_with_debate(settings, system_prompt, user_content, history=None):
    """Simulates an expert council debate between MoF Inspector and Independent Tax Auditor."""
    json_instruction = (
        "\n\nBẮT BUỘC TRẢ VỀ kết quả dưới dạng một chuỗi JSON hợp lệ duy nhất có cấu trúc sau (không kèm ký tự markdown như ```json hay bất kỳ văn bản thừa nào ngoài JSON):\n"
        "{\n"
        '  "debate": [\n'
        '    {"speaker": "Thanh tra Bộ Tài chính", "text": "Ý kiến của Thanh tra từ khía cạnh tuân thủ luật pháp nghiêm ngặt, phòng tránh rủi ro vi phạm..."},\n'
        '    {"speaker": "Kiểm toán viên độc lập", "text": "Ý kiến của Kiểm toán viên về tối ưu hóa lợi ích doanh nghiệp, chứng từ và thực tế kế toán..."}\n'
        '  ],\n'
        '  "consensus_summary": "Tóm tắt ngắn gọn điểm đồng thuận chính giữa 2 chuyên gia (1-2 câu)...",\n'
        '  "response": "Câu trả lời chi tiết, chính xác và đầy đủ nhất dành cho người dùng về vấn đề này (kèm trích dẫn pháp lý chi tiết)..."\n'
        "}"
    )
    
    modified_system_prompt = system_prompt + json_instruction
    
    try:
        raw_response = call_llm(settings, modified_system_prompt, user_content, history=history)
        parsed = clean_and_parse_json(raw_response)
        if parsed and isinstance(parsed, dict) and "response" in parsed:
            return parsed
    except Exception as e:
        print(f"Error calling LLM with debate: {e}")

    # Fallback if parsing or LLM fails
    try:
        # Attempt to get a normal response first
        normal_response = call_llm(settings, system_prompt, user_content, history=history)
    except Exception as e:
        normal_response = f"Xin lỗi, tôi gặp lỗi kết nối với mô hình AI: {str(e)}"
        
    fallback_debate = [
        {
            "speaker": "Thanh tra Bộ Tài chính",
            "text": f"Đối với câu hỏi về '{user_content[:60]}...', chúng tôi yêu cầu doanh nghiệp tuân thủ nghiêm ngặt các văn bản hướng dẫn và thông tư hiện hành."
        },
        {
            "speaker": "Kiểm toán viên độc lập",
            "text": "Từ góc độ thực tế kế toán, doanh nghiệp cần chuẩn bị đầy đủ chứng từ chứng minh tính hợp lý, hợp lệ của khoản chi để giải trình khi quyết toán."
        }
    ]
    return {
        "debate": fallback_debate,
        "consensus_summary": "Doanh nghiệp cần kết hợp giữa việc tuân thủ các quy định pháp lý và hoàn thiện hồ sơ chứng từ thực tế.",
        "response": normal_response
    }

