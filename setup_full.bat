@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%dubbing-backend"
set "FRONTEND_DIR=%ROOT%dubbing-frontend"
set "BACKEND_PY=%BACKEND_DIR%\venv\Scripts\python.exe"

echo ========================================
echo Dubbing Extractor - Full Setup
echo ========================================
echo.
echo Tech stack:
echo - Backend: FastAPI, Socket.IO, Whisper, yt-dlp, FFmpeg, VieNeu-TTS
echo - Frontend: React 18, Vite, Zustand, React Query, TailwindCSS
echo - Runtime: Python venv + Node.js npm
echo.

where python >nul 2>&1 || (
    echo ERROR: Python not found in PATH.
    exit /b 1
)

where npm >nul 2>&1 || (
    echo ERROR: npm not found in PATH.
    exit /b 1
)

if not exist "%BACKEND_DIR%\venv" (
    echo Creating backend virtual environment...
    python -m venv "%BACKEND_DIR%\venv"
    if errorlevel 1 exit /b 1
)

echo Installing backend dependencies...
call "%BACKEND_DIR%\venv\Scripts\activate.bat"
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r "%BACKEND_DIR%\requirements-full.txt"
if errorlevel 1 (
    echo ERROR: Backend dependency install failed.
    exit /b 1
)

if not exist "%BACKEND_DIR%\.env" (
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
)

if not exist "%BACKEND_DIR%\bin\ffmpeg\ffmpeg.exe" (
    echo WARNING: Local FFmpeg binaries not found in dubbing-backend\bin\ffmpeg
    echo Run install_ffmpeg_local.ps1 after setup if backend cannot find FFmpeg.
)

echo Installing frontend dependencies...
cd /d "%FRONTEND_DIR%"
call npm.cmd install
if errorlevel 1 (
    echo ERROR: Frontend dependency install failed.
    exit /b 1
)

if not exist "%FRONTEND_DIR%\.env" (
    copy "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul
)

cd /d "%ROOT%"
echo.
echo ========================================
echo Setup complete
echo ========================================
echo Next:
echo 1. If needed, install FFmpeg with install_ffmpeg_local.ps1
echo 2. Start services with start_all.bat
echo 3. Open http://127.0.0.1:5173
echo ========================================
exit /b 0
