@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%dubbing-backend"
set "FRONTEND_DIR=%ROOT%dubbing-frontend"
set "BACKEND_PY=%BACKEND_DIR%\venv\Scripts\python.exe"
set "NPM_CMD=npm.cmd"
set "LOCAL_FFMPEG=%BACKEND_DIR%\bin\ffmpeg\ffmpeg.exe"
set "LOCAL_FFPROBE=%BACKEND_DIR%\bin\ffmpeg\ffprobe.exe"

echo ========================================
echo Dubbing Extractor - Full Setup
echo ========================================
echo.
echo Tech stack:
echo - Backend: FastAPI, Socket.IO, Whisper, yt-dlp, FFmpeg, VieNeu-TTS
echo - Frontend: React 18, Vite, Zustand, React Query, TailwindCSS
echo - Runtime: Python 3.10+ ^| Node 18+ ^| local venv ^| npm
echo.

where python >nul 2>&1 || (
    echo ERROR: Python not found in PATH.
    exit /b 1
)

where node >nul 2>&1 || (
    echo ERROR: Node.js not found in PATH.
    exit /b 1
)

where %NPM_CMD% >nul 2>&1 || (
    echo ERROR: npm.cmd not found in PATH.
    exit /b 1
)

echo Checking Python version...
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.10+ is required.
    python --version
    exit /b 1
)
python --version

echo Checking Node.js version...
node -e "const major=parseInt(process.versions.node.split('.')[0],10); process.exit(major>=18?0:1)"
if errorlevel 1 (
    echo ERROR: Node.js 18+ is required.
    node --version
    exit /b 1
)
node --version
call %NPM_CMD% --version
if errorlevel 1 (
    echo ERROR: npm.cmd is present but could not run.
    exit /b 1
)

if not exist "%BACKEND_DIR%\venv" (
    echo Creating backend virtual environment...
    python -m venv "%BACKEND_DIR%\venv"
    if errorlevel 1 (
        echo ERROR: Failed to create backend virtual environment.
        exit /b 1
    )
)

echo Preparing backend directories...
if not exist "%BACKEND_DIR%\bin\ffmpeg" mkdir "%BACKEND_DIR%\bin\ffmpeg"
if not exist "%ROOT%storage" mkdir "%ROOT%storage"
if not exist "%ROOT%temp" mkdir "%ROOT%temp"
if not exist "%ROOT%output" mkdir "%ROOT%output"

echo Installing backend dependencies...
call "%BACKEND_DIR%\venv\Scripts\activate.bat"
python -m pip install --upgrade pip wheel "setuptools<82"
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip tooling.
    exit /b 1
)

python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 (
    echo ERROR: Failed to install CPU PyTorch.
    exit /b 1
)

python -m pip install -r "%BACKEND_DIR%\requirements-full.txt"
if errorlevel 1 (
    echo ERROR: Backend dependency install failed.
    exit /b 1
)

if not exist "%BACKEND_DIR%\.env" (
    if exist "%BACKEND_DIR%\.env.example" (
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
    )
)

echo Ensuring FFmpeg is available...
if exist "%LOCAL_FFMPEG%" if exist "%LOCAL_FFPROBE%" goto :ffmpeg_ok
where ffmpeg >nul 2>&1
if not errorlevel 1 (
    where ffprobe >nul 2>&1
    if not errorlevel 1 goto :ffmpeg_ok
)

if exist "%ROOT%install_ffmpeg_local.ps1" (
    echo FFmpeg not found. Installing local FFmpeg...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%install_ffmpeg_local.ps1"
    if errorlevel 1 (
        echo ERROR: Failed to install local FFmpeg.
        exit /b 1
    )
) else (
    echo ERROR: FFmpeg not found and install_ffmpeg_local.ps1 is missing.
    exit /b 1
)

:ffmpeg_ok
if exist "%LOCAL_FFMPEG%" (
    echo Using local FFmpeg: %LOCAL_FFMPEG%
) else (
    echo Using FFmpeg from PATH.
)

echo Running backend smoke checks...
python -c "import sys; from pathlib import Path; sys.path.insert(0, r'%BACKEND_DIR%'); import app.main; from src.modules.video_processing.ffmpeg_wrapper import ffmpeg_cmd, ffprobe_cmd; print('backend_ok'); print(ffmpeg_cmd()); print(ffprobe_cmd())"
if errorlevel 1 (
    echo ERROR: Backend smoke test failed.
    exit /b 1
)

echo Installing frontend dependencies...
cd /d "%FRONTEND_DIR%"
call %NPM_CMD% install
if errorlevel 1 (
    echo ERROR: Frontend dependency install failed.
    exit /b 1
)

if not exist "%FRONTEND_DIR%\.env" (
    if exist "%FRONTEND_DIR%\.env.example" (
        copy "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul
    )
)

echo Running frontend build verification...
call %NPM_CMD% run build
if errorlevel 1 (
    echo ERROR: Frontend build verification failed.
    exit /b 1
)

cd /d "%ROOT%"
echo.
echo ========================================
echo Setup complete
echo ========================================
echo Verified:
echo - Python 3.10+
echo - Node 18+
echo - backend venv + full Python deps
echo - FFmpeg available
echo - backend import smoke test
echo - frontend npm install + production build
echo.
echo Next:
echo 1. Start services with start_all.bat
echo 2. Open http://127.0.0.1:5173
echo 3. If Redis is not running, processing still falls back to sync mode
echo ========================================
exit /b 0
