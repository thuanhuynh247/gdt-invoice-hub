#!/usr/bin/env python
"""
GDT Invoice Download Webapp - Local Launcher
Automatically activates virtual environment, boots the Flask application,
and opens the default web browser to the application dashboard.
"""

import os
import sys
import subprocess
import time
import webbrowser
import socket

def is_port_in_use(port: int) -> bool:
    """Check if the given port is already being used."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def get_python_executable():
    """Retrieve the correct Python executable inside the virtual environment."""
    if os.name == 'nt':  # Windows
        venv_python = os.path.join("venv", "Scripts", "python.exe")
    else:  # macOS/Linux
        venv_python = os.path.join("venv", "bin", "python")
        
    if os.path.exists(venv_python):
        print(f" Detected virtual environment Python: {venv_python}")
        return venv_python
    
    print("⚠️  Warning: venv directory not found! Falling back to system Python.")
    return sys.executable

def main():
    print("=" * 60)
    print("🚀 GDT INVOICE HUB - KHỞI CHẠY HỆ THỐNG CỤC BỘ (LOCAL)")
    print("=" * 60)
    
    port = 5000
    if is_port_in_use(port):
        print(f"❌ Error: Cổng {port} hiện đang được sử dụng bởi một ứng dụng khác.")
        print("Vui lòng tắt ứng dụng đang chiếm cổng hoặc giải phóng cổng trước khi chạy.")
        sys.exit(1)
        
    python_bin = get_python_executable()
    
    # Run server as a subprocess
    print("⚙️  Đang khởi động Flask Development Server...")
    server_process = subprocess.Popen(
        [python_bin, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Wait for the server to spin up
    print("⏳ Đang chờ máy chủ nội bộ sẵn sàng...")
    time.sleep(1.5)
    
    url = f"http://127.0.0.1:{port}"
    print(f"✨ Hệ thống đã sẵn sàng tại địa chỉ: {url}")
    print(f"🌐 Đang tự động mở trình duyệt mặc định của bạn...")
    
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"⚠️  Không thể tự động mở trình duyệt: {e}")
        print(f"Vui lòng truy cập thủ công tại: {url}")
        
    print("\n[NHẤN CTRL+C ĐỂ DỪNG MÁY CHỦ BẤT CỨ LÚC NÀO]")
    print("-" * 60)
    
    try:
        # Stream the Flask server log output directly to console
        while True:
            line = server_process.stdout.readline()
            if not line and server_process.poll() is not None:
                break
            if line:
                print(line.strip())
    except KeyboardInterrupt:
        print("\n\n🛑 Đang nhận lệnh dừng hệ thống...")
    finally:
        print("🔌 Đang ngắt Flask server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Đã tắt máy chủ nội bộ sạch sẽ. Hẹn gặp lại!")
        print("=" * 60)

if __name__ == "__main__":
    main()
