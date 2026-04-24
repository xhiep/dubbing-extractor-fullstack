@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%dubbing-backend"
set "FRONTEND_DIR=%ROOT%dubbing-frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"
set "BACKEND_URL=http://127.0.0.1:%BACKEND_PORT%"

echo ========================================
echo Dubbing Extractor - Start All
echo ========================================
echo.

if not exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    echo ERROR: Backend venv not found at "%BACKEND_DIR%\venv"
    echo Run setup_full.bat first.
    exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
    echo ERROR: Frontend dependencies not found at "%FRONTEND_DIR%\node_modules"
    echo Run setup_full.bat first.
    exit /b 1
)

echo Stopping old frontend/backend processes first...
call "%ROOT%stop_all.bat" >nul 2>&1

echo Starting backend on port %BACKEND_PORT%...
start "Dubbing Backend" cmd /k "cd /d "%BACKEND_DIR%" && call venv\Scripts\activate.bat && python -m uvicorn app.main:asgi_app --host 127.0.0.1 --port %BACKEND_PORT%"

echo Waiting for backend health check...
set "BACKEND_OK="
for /l %%i in (1,1,20) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing '%BACKEND_URL%/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
    if not errorlevel 1 (
        set "BACKEND_OK=1"
        goto :backend_ready
    )
    timeout /t 1 /nobreak >nul
)

:backend_ready
if not defined BACKEND_OK (
    echo ERROR: Backend did not become healthy on %BACKEND_URL%
    exit /b 1
)

echo Starting frontend on port %FRONTEND_PORT%...
start "Dubbing Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && set VITE_PROXY_TARGET=%BACKEND_URL% && npm.cmd run dev -- --host 127.0.0.1 --port %FRONTEND_PORT%"

echo.
echo ========================================
echo Services started
echo ========================================
echo Backend:  %BACKEND_URL%
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo API Docs: %BACKEND_URL%/docs
echo ========================================
exit /b 0
