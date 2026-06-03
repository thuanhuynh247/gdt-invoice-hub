#!/usr/bin/env python3
"""
GDT Invoice Hub — Interactive Lego Setup Wizard
Allows users to choose installation components modularly, writes custom .env
and dynamically builds requirements.txt to optimize package downloads.
"""

import os
import sys
import secrets
import shutil
import sqlite3

# Define text colors for terminal
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

BANNER = f"""
{BLUE}{BOLD}  ____ ____ _____   ___                     _             _   _       _     
 / ___|  _ \\_   _| |_ _|_ ____   _____  ___| |_  /\\/\\    | | | |_   _| |__  
| |  _| | | || |    | || '_ \\ \\ / / _ \\/ __| __|/    \\   | |_| | | | | '_ \\ 
| |_| | |_| || |    | || | | \\ V / (_) \\__ \\ |_/ /\\/\\ \\  |  _  | |_| | |_) |
 \\____|____/ |_|   |___|_| |_|\\_/ \\___/|___/\\__\\/    \\/  |_| |_|\\__,_|_.__/ 
                                                                            {RESET}
                    {CYAN}--- DỰ ÁN WEBAPP ĐỒNG BỘ HÓA ĐƠN GDT ---{RESET}
              {YELLOW}--- CẤU TRÚC LEGO LẮP GHÉP / MODULAR SETUP WIZARD ---{RESET}
"""

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_input(prompt: str, default: str = "") -> str:
    placeholder = f" [{default}]" if default else ""
    val = input(f"{BOLD}{prompt}{placeholder}:{RESET} ").strip()
    return val if val else default

def get_bool(prompt: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    while True:
        val = input(f"{BOLD}{prompt} ({default_str}):{RESET} ").strip().lower()
        if not val:
            return default
        if val in ['y', 'yes', 't', 'true', '1']:
            return True
        if val in ['n', 'no', 'f', 'false', '0']:
            return False
        print(f"{RED}Vui lòng chỉ nhập Y hoặc N.{RESET}")

def main():
    clear_screen()
    print(BANNER)
    print("Chào mừng bạn đến với trình cấu hình Lego của GDT Invoice Hub!")
    print("Trình cài đặt này sẽ giúp bạn thiết lập ứng dụng với các thành phần tùy chọn.")
    print("Nhờ đó, bạn có thể loại bỏ các thư viện nặng ký không dùng đến (như ddddocr) để tăng tốc độ cài đặt.\n")

    # Step 1: Selection Mode
    print(f"{BOLD}CHỌN PHƯƠNG THỨC THIẾT LẬP:{RESET}")
    print("  1. Cài đặt đầy đủ (Khuyên dùng - Bật tất cả các tính năng)")
    print("  2. Cài đặt tùy chỉnh Lego (Lựa chọn từng mảnh ghép tính năng)\n")
    
    choice = ""
    while choice not in ["1", "2"]:
        choice = get_input("Nhập lựa chọn của bạn (1 hoặc 2)", "1")

    # Default Lego Component Toggles
    components = {
        "captcha_solver": True,
        "ai_advisor": True,
        "ocr_pipeline": True,
        "sync_daemon": True,
        "api_gateway": True
    }

    if choice == "2":
        clear_screen()
        print(BANNER)
        print(f"{CYAN}--- LỰA CHỌN CẤU PHẦN LEGO ---{RESET}\n")
        
        components["captcha_solver"] = get_bool("1. Bật tính năng Tự Động Giải CAPTCHA Ngoại Tuyến (Yêu cầu thư viện ddddocr, reportlab)?", True)
        if not components["captcha_solver"]:
            print(f"   {YELLOW}» Đã tắt ddddocr. Captcha khi đăng nhập live sẽ được nhập tay thủ công.{RESET}\n")
            
        components["ai_advisor"] = get_bool("2. Bật Trợ Lý AI & Tìm kiếm Luật Thuế Hoãn Lại RAG (FTS5 + PDF Ingestion)?", True)
        components["ocr_pipeline"] = get_bool("3. Bật Pipeline OCR quét hóa đơn ảnh/giấy (Gemini/Ollama)?", True)
        components["sync_daemon"] = get_bool("4. Bật Background Sync Daemon & Scheduler (Đồng bộ MST tự động chạy ngầm)?", True)
        components["api_gateway"] = get_bool("5. Bật REST API Gateway & Webhook Hub cho lập trình viên?", True)

    # Step 2: Basic Configuration
    clear_screen()
    print(BANNER)
    print(f"{CYAN}--- CẤU HÌNH HỆ THỐNG CƠ BẢN ---{RESET}\n")

    port = get_input("Cấu hình Port hoạt động cho Webapp", "5000")
    
    use_mock = get_bool("Chạy ở chế độ MOCK (Chạy offline không cần kết nối cổng Thuế thật)?", True)
    
    username = ""
    password = ""
    if not use_mock:
        print(f"\n{YELLOW}Hãy nhập thông tin đăng nhập Tổng Cục Thuế của bạn:{RESET}")
        username = get_input("Mã số thuế doanh nghiệp (Username)")
        password = get_input("Mật khẩu tài khoản GDT Portal")
        
    api_provider = "ollama"
    gemini_key = ""
    if components["ai_advisor"] or components["ocr_pipeline"]:
        print(f"\n{CYAN}--- CẤU HÌNH TRÍ TUỆ NHÂN TẠO (AI/RAG) ---{RESET}")
        api_provider = get_input("Chọn AI Provider (gemini hoặc ollama)", "ollama").lower()
        if api_provider == "gemini":
            gemini_key = get_input("Nhập API Key của Gemini")

    # Step 3: Write Custom .env
    print(f"\n{GREEN}» Đang tạo tệp cấu hình môi trường .env...{RESET}")
    
    flask_secret = secrets.token_hex(24)
    jwt_secret = secrets.token_hex(24)
    encryption_key = secrets.token_urlsafe(32)[:32] # 32 bytes

    env_content = f"""# ============================================================
# GDT Invoice Hub — Lego Customized Environment Configuration
# Generated automatically by setup_wizard.py
# ============================================================

# ── Flask Core ───────────────────────────────────────────────
FLASK_SECRET_KEY={flask_secret}
FLASK_DEBUG=false
PORT={port}

# ── GDT Portal Connection ────────────────────────────────────
GDT_BASE_URL=https://hoadondientu.gdt.gov.vn
GDT_USE_MOCK={'true' if use_mock else 'false'}
GDT_TIMEOUT_SECONDS=30
GDT_USERNAME={username}
GDT_PASSWORD={password}

# ── Lego Component Switches ──────────────────────────────────
AUTO_SOLVE_CAPTCHA={'true' if components["captcha_solver"] else 'false'}
ENABLE_CAPTCHA_PREFETCH={'true' if components["captcha_solver"] else 'false'}
ENABLE_SCHEDULER_WORKER={'true' if components["sync_daemon"] else 'false'}
ENABLE_PDF_INGESTION={'true' if components["ai_advisor"] else 'false'}
ENABLE_SYNC_DAEMON={'true' if components["sync_daemon"] else 'false'}
ENABLE_API_GATEWAY={'true' if components["api_gateway"] else 'false'}

# ── AI / LLM Configuration ───────────────────────────────────
AI_PROVIDER={api_provider}
GEMINI_API_KEY={gemini_key}
OLLAMA_API_URL=http://localhost:11434
AI_MODEL_NAME={'gemini-1.5-flash' if api_provider == 'gemini' else 'llava'}

# ── Security & Cryptography ──────────────────────────────────
ENCRYPTION_KEY={encryption_key}
JWT_SECRET={jwt_secret}
"""

    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"{GREEN}✔ Đã ghi thành công .env{RESET}")

    # Step 4: Dynamically Build requirements.txt
    print(f"\n{GREEN}» Đang xây dựng danh sách dependencies tối ưu (requirements.txt)...{RESET}")
    
    base_requirements = [
        "Flask==3.1.1",
        "requests==2.32.3",
        "selenium==4.32.0",
        "openpyxl==3.1.5",
        "python-dotenv==1.1.0",
        "beautifulsoup4==4.13.4",
        "pytest==8.3.5",
        "pytest-cov==6.1.1",
        "lxml==6.1.1",
        "cryptography==42.0.5",
        "Flask-SQLAlchemy==3.1.1",
        "xhtml2pdf>=0.2.16",
        "pypdf>=4.0.0"
    ]

    # Lego-specific dependencies
    if components["captcha_solver"]:
        base_requirements.append("ddddocr==1.6.1")
        base_requirements.append("svglib==1.6.0")
        base_requirements.append("reportlab==4.5.1")
        
    if api_provider == "gemini":
        base_requirements.append("google-generativeai>=0.5.0")

    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(base_requirements) + "\n")
    print(f"{GREEN}✔ Đã ghi thành công requirements.txt (Đã tối ưu hóa danh sách gói tải về){RESET}")

    # Step 5: Database Seeding & Verification
    print(f"\n{GREEN}» Đang khởi tạo cơ sở dữ liệu và thư mục hệ thống...{RESET}")
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/temp", exist_ok=True)
    os.makedirs("data/invoices_xml", exist_ok=True)

    # Preflight Check Trigger
    print(f"\n{CYAN}--- KHỞI CHẠY KIỂM TRA PRE-FLIGHT ---{RESET}")
    try:
        import subprocess
        python_exec = sys.executable
        res = subprocess.run([python_exec, "scripts/preflight_checks.py"], capture_output=False, text=True)
        if res.returncode == 0:
            print(f"\n{GREEN}🎉 Chúc mừng! Lego Setup của bạn đã sẵn sàng hoạt động.{RESET}")
        else:
            print(f"\n{YELLOW}⚠️ Setup hoàn thành với một số cảnh báo kiểm toán.{RESET}")
    except Exception as e:
        print(f"\n{RED}Không thể khởi chạy preflight_checks tự động: {e}{RESET}")

    print(f"\n{BOLD}CÁC BƯỚC TIẾP THEO:{RESET}")
    print(f"  1. Kích hoạt môi trường ảo:  {CYAN}.\\venv\\Scripts\\activate{RESET} (Windows) hoặc {CYAN}source venv/bin/activate{RESET} (Unix)")
    print(f"  2. Cài đặt các gói:          {CYAN}pip install -r requirements.txt{RESET}")
    print(f"  3. Khởi chạy ứng dụng:      {CYAN}python app.py{RESET}")
    print(f"  4. Mở trình duyệt truy cập:  {CYAN}http://127.0.0.1:{port}{RESET}\n")

if __name__ == "__main__":
    main()
