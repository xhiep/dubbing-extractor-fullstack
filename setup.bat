@echo off
REM Setup script for first-time installation
setlocal enabledelayedexpansion

echo ========================================
echo Dubbing Extractor - First Time Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found!
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] Setting up Backend...
cd dubbing-backend

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        cd ..
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    cd ..
    pause
    exit /b 1
)

echo Installing minimal dependencies...
pip install -r requirements-minimal.txt
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies!
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo [2/4] Setting up Frontend...
cd dubbing-frontend

echo Installing npm packages...
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies!
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo [3/4] Creating .env files...

REM Backend .env
if not exist "dubbing-backend\.env" (
    echo Creating backend .env...
    copy dubbing-backend\.env.example dubbing-backend\.env >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Could not create backend .env file
    )
)

REM Frontend .env
if not exist "dubbing-frontend\.env" (
    echo Creating frontend .env...
    copy dubbing-frontend\.env.example dubbing-frontend\.env >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Could not create frontend .env file
    )
)

echo.
echo [4/4] Setup complete!
echo.
echo ========================================
echo Next Steps:
echo ========================================
echo 1. Run: start_all.bat
echo 2. Open: http://localhost:5173
echo.
echo Optional - Install full features:
echo   cd dubbing-backend
echo   venv\Scripts\activate
echo   pip install -r requirements.txt
echo ========================================
pause
