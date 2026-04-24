@echo off
REM Start FastAPI server for local development
REM No Docker required

echo Starting Dubbing Extractor Backend (Local Dev)...
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements-minimal.txt
    pause
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

REM Check if FastAPI is installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo ERROR: FastAPI not installed!
    echo Please install dependencies:
    echo   pip install -r requirements-minimal.txt
    pause
    exit /b 1
)

REM Start server
echo Server starting at http://localhost:8000
echo API docs at http://localhost:8000/docs
echo Press Ctrl+C to stop
echo.

uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload
