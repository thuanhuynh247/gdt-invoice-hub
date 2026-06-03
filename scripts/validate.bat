@echo off
setlocal enabledelayedexpansion

:: Redirect temp directories to workspace folder on D: drive due to full C: drive
set TEMP=%~dp0..\data\temp
set TMP=%~dp0..\data\temp
if not exist "%TEMP%" mkdir "%TEMP%"

echo ===================================================
echo [HARNESS VALIDATE] Running Local Validation Gate...
echo ===================================================

:: Ensure script is run from the workspace root
if not exist "app.py" (
    echo [ERROR] Must run this script from the workspace root directory.
    exit /b 1
)

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at 'venv'.
    echo Please run 'SETUP.bat' first.
    exit /b 1
)

echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo [2/3] Checking python syntax in codebase...
python -m compileall -q app.py config.py run_local.py auth invoices export tests
if !errorlevel! neq 0 (
    echo [ERROR] Python syntax check failed!
    exit /b 1
)
echo [SUCCESS] Python syntax is valid.

echo [3/3] Running pytest suite...
if "%DISABLE_COVERAGE%"=="1" (
    echo [INFO] Running pytest without coverage to prevent Python 3.14 interpreter crashes...
    python -m pytest tests -v
) else (
    python -m pytest tests -v --cov=auth --cov=invoices --cov=export --cov=app --cov-report=term-missing
)
if !errorlevel! neq 0 (
    echo [ERROR] Pytest execution failed!
    exit /b 1
)

echo ===================================================
echo [SUCCESS] All validation checks passed successfully!
echo ===================================================
exit /b 0
