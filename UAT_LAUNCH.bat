@echo off
REM =========================================================
REM  GDT Invoice Hub - UAT Quick Launch Script
REM  Phiên bản: v17.0.0
REM  Mô tả: Khởi chạy nhanh hệ thống cho kiểm thử UAT
REM =========================================================

echo.
echo ========================================================
echo   GDT INVOICE HUB v17.0.0 - KHOI CHAY UAT
echo ========================================================
echo.

REM Chuyển đến thư mục dự án
cd /d "d:\LearnAnyThing\Webapp XML"

REM Kiểm tra Python
if not exist "venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay moi truong ao Python (venv)!
    echo Vui long chay: python -m venv venv
    pause
    exit /b 1
)

REM Kiểm tra port 5000
netstat -an | findstr ":5000" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [CANH BAO] Cong 5000 dang duoc su dung boi ung dung khac.
    echo Vui long tat ung dung do truoc khi chay.
    pause
    exit /b 1
)

echo [1/4] Kich hoat moi truong ao Python...
call venv\Scripts\activate

echo [2/4] Chay Kiem tra Tien Kien (Production Pre-flight Checks)...
python scripts\preflight_checks.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ^[CANH BAO^] Pre-flight checks da phat hien loi nghiem trong!
    set /p choice="Ban co muon tiep tuc chay he thong khong? (Y/N): "
    if /i "%choice%" NEQ "y" (
        echo [THONG TIN] Da huy khoi chay he thong do loi Pre-flight.
        pause
        exit /b 1
    )
)

echo [3/4] Chay UAT Smoke Test truoc khi khoi dong...
python scripts\uat_smoke_test.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Smoke Test that bai! Can sua loi truoc khi bat dau UAT.
    pause
    exit /b 1
)

echo.
echo [4/4] Khoi dong he thong...
echo.
echo   Truy cap tai: http://127.0.0.1:5000
echo   Nhan Ctrl+C de dung he thong
echo.
python run_local.py

pause
