@echo off
REM Stop all running services

echo Stopping Dubbing Extractor services...

REM Kill uvicorn (backend)
taskkill /FI "WINDOWTITLE eq Dubbing Backend*" /F 2>nul
if %errorlevel% equ 0 (
    echo Backend stopped.
) else (
    echo Backend not running.
)

REM Kill npm/vite (frontend)
taskkill /FI "WINDOWTITLE eq Dubbing Frontend*" /F 2>nul
if %errorlevel% equ 0 (
    echo Frontend stopped.
) else (
    echo Frontend not running.
)

echo.
echo All services stopped.
pause
