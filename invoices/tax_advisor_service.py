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
