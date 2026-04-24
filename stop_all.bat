@echo off
setlocal

echo ========================================
echo Dubbing Extractor - Stop All
echo ========================================

for %%P in (5173 8000 8010) do (
    for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
        taskkill /PID %%I /F >nul 2>&1
    )
)

for %%T in ("Dubbing Backend" "Dubbing Frontend") do (
    taskkill /FI "WINDOWTITLE eq %%~T*" /F >nul 2>&1
)

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -match 'python|node|npm|powershell') -and ($_.CommandLine -match 'dubbing-extractor-fullstack' -or $_.CommandLine -match 'uvicorn app.main:asgi_app' -or $_.CommandLine -match 'vite.js') } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }" >nul 2>&1

echo Backend/frontend processes stopped.
exit /b 0
