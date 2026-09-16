@echo off
cd /d "%~dp0..\backend"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt
celery -A app.worker.celery_app worker --loglevel=info --pool=solo
