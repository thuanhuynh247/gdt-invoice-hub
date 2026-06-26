@echo off
title Cố Vấn Thuế AI - meInvoice Intelligence
chcp 65001 > nul
echo ==========================================================
echo  Đang khởi động Cố Vấn Thuế AI (Local RAG Console Client)
echo ==========================================================
echo.
.\venv\Scripts\python.exe scripts\local_chatbot.py
if errorlevel 1 (
    echo.
    echo [Lỗi] Không thể khởi động chatbot. Vui lòng kiểm tra xem virtual environment (venv) đã được cài đặt và hoạt động chưa.
    pause
)
