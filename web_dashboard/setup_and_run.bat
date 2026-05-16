@echo off
echo ========================================
echo    TRADING DASHBOARD - FIRST TIME SETUP
echo ========================================
echo.
echo This will install required software and start the dashboard.
echo.

echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo    Python found!

echo.
echo [2/6] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo    Node.js found!

echo.
echo [3/6] Installing Backend Dependencies...
cd /d "%~dp0backend"
pip install -q -r requirements.txt 2>nul
if errorlevel 1 (
    echo WARNING: Some backend packages may not have installed.
) else (
    echo    Backend dependencies installed!
)

echo.
echo [4/6] Installing Frontend Dependencies...
cd /d "%~dp0frontend"
if not exist node_modules (
    echo    This may take a few minutes...
    npm install --silent 2>nul
) else (
    echo    Frontend dependencies already installed!
)

echo.
echo [5/6] Cleaning up old processes...
:: Kill existing backend on port 8000
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %a >nul 2>&1
)
:: Kill existing node processes
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo [6/6] Starting Dashboard...
echo.
cd /d "%~dp0"
call run.bat

echo.
echo Done!
pause