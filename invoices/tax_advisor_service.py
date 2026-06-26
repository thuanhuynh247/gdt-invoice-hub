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


def get_specialized_agent(query: str) -> tuple[str, str]:
    """Classify user query and return specialized agent name and system prompt instructions."""
    q = query.lower()
    
    # 1. VAT (Value Added Tax)
    vat_keywords = ["gtgt", "giá trị gia tăng", "khấu trừ", "hoàn thuế", "vat", "suất", "8%", "10%", "đầu vào", "đầu ra"]
    # 2. CIT (Corporate Income Tax)
    cit_keywords = ["tndn", "thu nhập doanh nghiệp", "chi phí được trừ", "chi phí hợp lý", "miễn thuế", "cit", "lỗ", "kết chuyển"]
    # 3. PIT (Personal Income Tax)
    pit_keywords = ["tncn", "thu nhập cá nhân", "giảm trừ gia cảnh", "lương", "pit", "nhân sự", "lao động", "hợp đồng"]
    # 4. Invoicing & Documents
    inv_keywords = ["hóa đơn", "biên bản", "sai sót", "điều chỉnh", "thay thế", "hủy hóa đơn", "ký hiệu", "mẫu số", "nghị định 123", "thông tư 78", "nky", "tthai", "mccqt"]
    
    if any(k in q for k in vat_keywords):
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
            
        sql = """
            SELECT chunk_content, document_source, page_number
            FROM tax_regulation_fts
            WHERE tax_regulation_fts MATCH ?
            ORDER BY bm25(tax_regulation_fts) ASC
            LIMIT 3;
        """
        cursor.execute(sql, (clean_q,))
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
    except Exception:
        pass
    finally:
        conn.close()
    return "", []

def call_llm(settings, system_prompt, user_content):
    provider = settings.get("ai_provider", "ollama").lower()
    model_name = settings.get("ai_model_name", "gemma-4")
    api_key_cipher = settings.get("ai_api_key", "")
    
    api_key = ""
    if api_key_cipher:
        try:
            api_key = decrypt_password(api_key_cipher)
        except Exception:
            api_key = api_key_cipher

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

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
