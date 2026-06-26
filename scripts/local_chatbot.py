#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import requests
import json
import re
from datetime import datetime

# Set path so we can import auth.crypto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from auth.crypto import decrypt_password, encrypt_password
except ImportError:
    # Fallback if import fails
    def decrypt_password(ciphertext):
        return ciphertext
    def encrypt_password(password):
        return password

# Import Rich elements
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.status import Status
    from rich.theme import Theme
except ImportError:
    print("Error: Library 'rich' is not installed in the environment. Please run: pip install rich")
    sys.exit(1)

# Custom Theme
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "law": "bold yellow",
    "header": "bold cyan"
})

console = Console(theme=custom_theme)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.db")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        console.print(f"[danger]Lỗi:[/danger] Không tìm thấy cơ sở dữ liệu tại {DB_PATH}")
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
    except Exception as e:
        console.print(f"[warning]Cảnh báo:[/warning] Không thể đọc cài đặt từ DB: {e}. Sử dụng cấu hình mặc định.")
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
    except Exception as e:
        console.print(f"[danger]Lỗi khi lưu cài đặt vào DB:[/danger] {e}")
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
    except Exception as e:
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

def list_documents():
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tax_regulation_chunk'")
        if not cursor.fetchone():
            console.print("[warning]Không tìm thấy bảng lưu trữ văn bản luật tax_regulation_chunk.[/warning]")
            return
            
        cursor.execute("""
            SELECT document_source, COUNT(*), MIN(page_number), MAX(page_number)
            FROM tax_regulation_chunk
            GROUP BY document_source
        """)
        rows = cursor.fetchall()
        
        table = Table(title="Danh Sách Văn Bản Luật Đã Ingest", show_header=True, header_style="bold green")
        table.add_column("Tên Tài Liệu", style="yellow")
        table.add_column("Số Lượng Chunks", justify="right", style="cyan")
        table.add_column("Phạm Vi Trang", justify="center", style="magenta")
        
        for r in rows:
            source, count, min_p, max_p = r
            table.add_row(source, str(count), f"Trang {min_p} - {max_p}")
            
        console.print(table)
    except Exception as e:
        console.print(f"[danger]Lỗi khi liệt kê tài liệu:[/danger] {e}")
    finally:
        conn.close()

def configure_ai_settings(settings):
    console.print("\n[header]=== Cấu hình thông số AI Trợ Lý ===[/header]")
    provider = Prompt.ask("Nhà cung cấp AI (ollama/openai/gemini)", default=settings.get("ai_provider", "ollama"), choices=["ollama", "openai", "gemini"])
    
    default_models = {
        "ollama": "gemma-4",
        "openai": "gpt-4o-mini",
        "gemini": "gemini-1.5-flash"
    }
    
    model_name = Prompt.ask("Tên model", default=settings.get("ai_model_name", default_models[provider]))
    
    api_key_cipher = settings.get("ai_api_key", "")
    api_key_plain = ""
    if api_key_cipher:
        try:
            api_key_plain = decrypt_password(api_key_cipher)
        except Exception:
            api_key_plain = api_key_cipher
            
    if provider in ["openai", "gemini"]:
        prompt_key = f"Nhập API Key {provider.upper()}"
        if api_key_plain:
            prompt_key += f" (để trống để giữ nguyên key hiện tại)"
        key_input = Prompt.ask(prompt_key, password=True, default="")
        if key_input:
            api_key_cipher = encrypt_password(key_input)
    else:
        api_key_cipher = ""
        
    ollama_endpoint = settings.get("ai_ollama_endpoint", "http://localhost:11434")
    if provider == "ollama":
        ollama_endpoint = Prompt.ask("Ollama Endpoint (URL)", default=ollama_endpoint)
        
    updated_settings = {
        "ai_enabled": True,
        "ai_provider": provider,
        "ai_model_name": model_name,
        "ai_api_key": api_key_cipher,
        "ai_ollama_endpoint": ollama_endpoint
    }
    
    if save_settings(updated_settings):
        console.print("[success]Lưu cấu hình thành công![/success]")
        return updated_settings
    else:
        console.print("[danger]Lưu cấu hình thất bại.[/danger]")
        return settings

def print_welcome_panel():
    welcome_text = Text()
    welcome_text.append("Chào mừng bạn đến với Cố Vấn Thuế AI cục bộ!\n", style="bold cyan")
    welcome_text.append("Hệ thống tự động sử dụng FTS5 RAG trên cơ sở dữ liệu luật thuế GTGT & TNDN để trả lời câu hỏi của bạn.\n", style="italic")
    welcome_text.append("\nNhập 'q' hoặc 'exit' để thoát | 'help' để xem các lệnh hỗ trợ.", style="dim")
    
    console.print(Panel(welcome_text, title="TAX AI ADVISOR - LOCAL CONSOLE CLIENT", border_style="green", expand=False))

def format_law_badges(text):
    text = re.sub(r'(Nghị định \d+/\d+/NĐ-CP)', r'[bold yellow]\1[/bold yellow]', text, flags=re.IGNORECASE)
    text = re.sub(r'(Thông tư \d+/\d+/TT-BTC)', r'[bold yellow]\1[/bold yellow]', text, flags=re.IGNORECASE)
    text = re.sub(r'(Luật số \d+/\d+/QH\d+|Luật Thuế GTGT \d+/\d+/QH\d+|Luật Thuế GTGT|Luật Thuế TNDN|Luật Quản lý thuế)', r'[bold yellow]\1[/bold yellow]', text, flags=re.IGNORECASE)
    text = re.sub(r'(Điều \d+(?:\s+Khoản\s+\d+)?)', r'[bold cyan]\1[/bold cyan]', text, flags=re.IGNORECASE)
    return text

def main():
    print_welcome_panel()
    settings = load_settings()
    
    # Display configuration
    console.print(f"[info]Nhà cung cấp AI:[/info] [bold white]{settings.get('ai_provider', 'ollama').upper()}[/bold white]")
    console.print(f"[info]Mô hình sử dụng:[/info] [bold white]{settings.get('ai_model_name', 'gemma-4')}[/bold white]")
    console.print(f"[info]Cơ sở dữ liệu:[/info] [bold white]{os.path.basename(DB_PATH)}[/bold white]")
    console.print("-" * 60)
    
    while True:
        try:
            query = Prompt.ask("\n[bold green]Kế toán[/bold green]")
            query_clean = query.strip()
            
            if not query_clean:
                continue
                
            if query_clean.lower() in ['q', 'exit', 'quit']:
                console.print("[success]Cảm ơn bạn đã sử dụng dịch vụ! Tạm biệt.[/success]")
                break
                
            if query_clean.lower() == 'help':
                console.print("\n[header]Các Lệnh Hỗ Trợ:[/header]")
                console.print("  [bold yellow]docs[/bold yellow] : Liệt kê các văn bản pháp luật đã nạp vào database")
                console.print("  [bold yellow]config[/bold yellow] : Hiển thị & chỉnh sửa cấu hình AI hiện tại")
                console.print("  [bold yellow]clear[/bold yellow] : Xóa sạch màn hình console")
                console.print("  [bold yellow]exit / q[/bold yellow] : Thoát ứng dụng")
                continue
                
            if query_clean.lower() == 'docs':
                list_documents()
                continue
                
            if query_clean.lower() == 'config':
                # Show current configs in clean table
                table = Table(title="Cấu Hình AI Hiện Tại", show_header=True, header_style="bold cyan")
                table.add_column("Tham số", style="yellow")
                table.add_column("Giá trị", style="white")
                for k, v in settings.items():
                    if k == "ai_api_key":
                        val = "********" if v else "Chưa thiết lập"
                    else:
                        val = str(v)
                    table.add_row(k, val)
                console.print(table)
                
                if Confirm.ask("Bạn có muốn chỉnh sửa cấu hình không?"):
                    settings = configure_ai_settings(settings)
                continue
                
            if query_clean.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                print_welcome_panel()
                continue
                
            # Perform RAG Search
            with Status("[cyan]Đang tra cứu luật thuế liên quan...", console=console) as status:
                rag_context, citations = get_rag_context(query_clean)
                
            if rag_context:
                console.print(f"[info]Tìm thấy ngữ cảnh luật liên quan. Đang soạn câu trả lời...[/info]")
            else:
                console.print(f"[info]Không tìm thấy tài liệu phù hợp trong FTS index. Sử dụng tri thức mặc định...[/info]")
                
            system_prompt = (
                "Bạn là Kế toán trưởng & Chuyên gia tư vấn thuế chuyên nghiệp (Senior Tax Compliance Consultant) của meInvoice Intelligence.\n"
                "Nhiệm vụ của bạn là giải đáp các thắc mắc về luật thuế, chính sách kế toán, quy định hóa đơn tại Việt Nam.\n"
                "Hãy luôn trả lời bằng giọng điệu chuyên nghiệp, chuẩn mực của một cố vấn thuế cấp cao. Trích dẫn chính xác các Điều, Khoản, Thông tư, Nghị định liên quan (ví dụ: Nghị định 123/2020/NĐ-CP về hóa đơn, Nghị định 125/2020/NĐ-CP về xử phạt hành chính thuế/hóa đơn, Thông tư 219/2013/TT-BTC về thuế GTGT, Luật Thuế GTGT mới 48/2024/QH15 hoặc Luật số 149/2025/QH15) khi đưa ra lời khuyên pháp lý.\n"
            )
            
            if rag_context:
                system_prompt += (
                    "Dưới đây là các tài liệu quy định pháp luật thuế liên quan được truy xuất từ cơ sở dữ liệu luật thuế (RAG Context):\n"
                    f"{rag_context}\n\n"
                    "Khi trả lời các câu hỏi về luật thuế, hãy:\n"
                    "- Trích dẫn chính xác các Điều, Khoản, Thông tư, Nghị định liên quan.\n"
                    "- Cung cấp giải thích rõ ràng, chuyên nghiệp và có chiều sâu bằng tiếng Việt.\n"
                    "- Đưa ra các khuyến nghị hoặc hành động cụ thể để giảm thiểu rủi ro pháp lý cho doanh nghiệp.\n\n"
                )
                
            system_prompt += (
                "Hãy trả lời bằng tiếng Việt tự nhiên, cực kỳ chuyên nghiệp, chính xác và có thể sử dụng định dạng bảng (Markdown Table) hoặc danh sách khi cần thiết.\n"
                "Nếu người dùng hỏi thông tin không liên quan đến hóa đơn thuế/kế toán doanh nghiệp, hãy phản hồi lịch sự rằng bạn chỉ hỗ trợ tư vấn thuế doanh nghiệp."
            )
            
            with Status("[cyan]Đang gọi AI xử lý...", console=console) as status:
                try:
                    response = call_llm(settings, system_prompt, query_clean)
                except Exception as e:
                    console.print(f"[danger]Lỗi gọi LLM:[/danger] {e}")
                    continue
                    
            console.print("\n" + "=" * 60)
            console.print("[bold yellow]Trợ lý AI:[/bold yellow]")
            markdown_content = format_law_badges(response)
            console.print(Markdown(markdown_content))
            
            # Print visual citations if available
            if citations:
                console.print("\n[bold info]📷 Tài liệu tham khảo trực quan (PixelRAG):[/bold info]")
                for idx, cit in enumerate(citations):
                    console.print(f"  {idx+1}. [yellow]{cit['source']}[/yellow] (Trang {cit['page']}) -> [dim]{os.path.basename(cit['img_path'])}[/dim]")
                
                # Ask if the user wants to open the visual document page
                if len(citations) == 1:
                    opt = Confirm.ask("Bạn có muốn mở xem ảnh trang tài liệu trực quan này không?", default=False)
                    if opt:
                        try:
                            os.startfile(citations[0]["img_path"])
                            console.print("[success]Đã mở ảnh chụp tài liệu gốc bằng trình xem mặc định.[/success]")
                        except Exception as e:
                            console.print(f"[danger]Không thể mở ảnh:[/danger] {e}")
                else:
                    opt_str = Prompt.ask("Nhập số thứ tự của tài liệu để mở xem (hoặc ấn Enter để bỏ qua)", default="")
                    if opt_str.isdigit():
                        idx = int(opt_str) - 1
                        if 0 <= idx < len(citations):
                            try:
                                os.startfile(citations[idx]["img_path"])
                                console.print("[success]Đã mở ảnh chụp tài liệu gốc bằng trình xem mặc định.[/success]")
                            except Exception as e:
                                console.print(f"[danger]Không thể mở ảnh:[/danger] {e}")
            console.print("=" * 60 + "\n")
            
        except KeyboardInterrupt:
            console.print("\n[warning]Đã dừng yêu cầu hiện tại.[/warning]")
        except Exception as e:
            console.print(f"[danger]Đã xảy ra lỗi hệ thống:[/danger] {e}")

if __name__ == '__main__':
    main()
