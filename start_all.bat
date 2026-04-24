@echo off
REM Start both Backend and Frontend for local development
REM No Docker required

echo ========================================
echo Dubbing Extractor - Full Stack Startup
echo ========================================
echo.

REM Check if backend venv exists
if not exist "dubbing-backend\venv\Scripts\activate.bat" (
    echo ERROR: Backend virtual environment not found!
    echo.
    echo Please setup backend first:
    echo   cd dubbing-backend
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements-minimal.txt
    echo.
    pause
    exit /b 1
)

REM Check if frontend node_modules exists
if not exist "dubbing-frontend\node_modules" (
    echo ERROR: Frontend dependencies not installed!
    echo.
    echo Please setup frontend first:
    echo   cd dubbing-frontend
    echo   npm install
    echo.
    pause
    exit /b 1
)

echo [1/2] Starting Backend (FastAPI)...
start "Dubbing Backend" cmd /k "cd dubbing-backend && venv\Scripts\activate && uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload"

REM Wait 3 seconds for backend to start
timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend (React + Vite)...
start "Dubbing Frontend" cmd /k "cd dubbing-frontend && npm run dev"

echo.
echo ========================================
echo Services Started!
echo ========================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Two terminal windows opened:
echo - Dubbing Backend (FastAPI)
echo - Dubbing Frontend (React)
echo.
echo Press Ctrl+C in each window to stop
echo ========================================
