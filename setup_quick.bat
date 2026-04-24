@echo off
REM Quick setup check and fix script

echo Checking setup...
echo.

REM Check if backend venv exists
if not exist "dubbing-backend\venv" (
    echo Backend venv not found. Creating...
    cd dubbing-backend
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements-minimal.txt
    cd ..
    echo Backend setup complete.
) else (
    echo Backend venv exists.
)

REM Check if frontend node_modules exists
if not exist "dubbing-frontend\node_modules" (
    echo Frontend node_modules not found. Installing...
    cd dubbing-frontend
    npm install
    cd ..
    echo Frontend setup complete.
) else (
    echo Frontend node_modules exists.
)

REM Check .env files
if not exist "dubbing-backend\.env" (
    echo Creating backend .env...
    copy dubbing-backend\.env.example dubbing-backend\.env >nul
)

if not exist "dubbing-frontend\.env" (
    echo Creating frontend .env...
    copy dubbing-frontend\.env.example dubbing-frontend\.env >nul
)

echo.
echo Setup check complete!
echo Run start_all.bat to start services.
pause
