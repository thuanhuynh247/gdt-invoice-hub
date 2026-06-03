@echo off
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo Setup complete. Edit .env if needed, then run: python app.py
