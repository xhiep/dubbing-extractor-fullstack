@echo off
REM Start Celery worker

cd /d "%~dp0"

REM Activate venv
call ..\venv\Scripts\activate.bat

REM Start Celery worker
celery -A app.tasks:celery_app worker --loglevel=info --concurrency=2 --pool=solo
