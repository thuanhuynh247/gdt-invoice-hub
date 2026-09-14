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

:: Check if virtual environment exists and activate if available
if exist "venv\Scripts\activate.bat" (
    echo [1/3] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [1/3] Using system Python environment...
)

echo [2/3] Checking python syntax in codebase...
python -m compileall -q app.py config.py run_local.py auth invoices export tests
if !errorlevel! neq 0 (
    echo [ERROR] Python syntax check failed!
    exit /b 1
)
echo [SUCCESS] Python syntax is valid.

python -c "import pytest_cov" >nul 2>&1
if !errorlevel! neq 0 set DISABLE_COVERAGE=1

if "!DISABLE_COVERAGE!"=="1" (
    echo [INFO] Running pytest without coverage...
    python -m pytest tests/test_v71_v75_features.py tests/test_lean_webapp_optimizer.py tests/test_v84_accounting_lean.py tests/test_v85_accounting_cockpit.py tests/test_v86_accounting_advanced.py -v
) else (
    python -m pytest tests/test_v71_v75_features.py tests/test_lean_webapp_optimizer.py tests/test_v84_accounting_lean.py tests/test_v85_accounting_cockpit.py tests/test_v86_accounting_advanced.py -v --cov=auth --cov=invoices --cov=export --cov=app --cov-report=term-missing
)
if !errorlevel! neq 0 (
    echo [ERROR] Pytest execution failed!
    exit /b 1
)

echo ===================================================
echo [SUCCESS] All validation checks passed successfully!
echo ===================================================
exit /b 0
