@echo off
REM Start FastAPI server with uvicorn

cd /d "%~dp0"

REM Activate venv (use parent venv with all dependencies)
call ..\venv\Scripts\activate.bat

REM Install backend-specific dependencies
pip install -q -r requirements.txt

REM Start uvicorn
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload
