#!/bin/bash
set -e

echo "==================================================="
echo "[HARNESS VALIDATE] Running Local Validation Gate..."
echo "==================================================="

# Ensure script is run from the workspace root
if [ ! -f "app.py" ]; then
    echo "[ERROR] Must run this script from the workspace root directory."
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ] && [ ! -f "venv/Scripts/activate" ]; then
    echo "[ERROR] Virtual environment not found."
    exit 1
fi

echo "[1/3] Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    source venv/Scripts/activate
fi

echo "[2/3] Checking python syntax in codebase..."
python -m compileall -q app.py config.py run_local.py auth invoices export tests
echo "[SUCCESS] Python syntax is valid."

echo "[3/3] Running pytest suite with coverage..."
python -m pytest tests -v --cov=auth --cov=invoices --cov=export --cov=app --cov-report=term-missing

echo "==================================================="
echo "[SUCCESS] All validation checks passed successfully!"
echo "==================================================="
exit 0
