@echo off
setlocal enabledelayedexpansion
title GT Trading Companion - Setup & Launch
color 0A

echo.
echo  ============================================================
echo     GT TRADING COMPANION - ONE CLICK SETUP
echo  ============================================================
echo.
echo  This will automatically set up and launch the trading dashboard.
echo.

:: -------------------------------------------
:: Step 1: Check Python
:: -------------------------------------------
echo  [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python is not installed or not in PATH!
    echo.
    echo  Please install Python 3.9+ from: https://www.python.org/downloads/
    echo  IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo        Python %PYTHON_VERSION% found.

:: -------------------------------------------
:: Step 2: Check Node.js
:: -------------------------------------------
echo  [2/6] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Node.js is not installed or not in PATH!
    echo.
    echo  Please install Node.js 16+ from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f %%v in ('node --version 2^>^&1') do set NODE_VERSION=%%v
echo        Node.js %NODE_VERSION% found.

:: -------------------------------------------
:: Step 3: Install Python dependencies
:: -------------------------------------------
echo  [3/6] Installing Python dependencies...
cd /d "%~dp0"

:: Install root requirements
echo        Installing root packages...
pip install -r requirements.txt --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    echo        [WARNING] Some root packages may have failed, continuing...
)

:: Install backend requirements
echo        Installing backend packages...
pip install -r web_dashboard\backend\requirements.txt --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    echo        [WARNING] Some backend packages may have failed, continuing...
)
echo        Python dependencies installed.

:: -------------------------------------------
:: Step 4: Install Node.js dependencies
:: -------------------------------------------
echo  [4/6] Installing frontend dependencies...
cd /d "%~dp0web_dashboard\frontend"

if not exist "node_modules" (
    echo        First time setup - installing npm packages (this may take a minute)...
    call npm install --silent 2>nul
    if errorlevel 1 (
        echo        [ERROR] npm install failed!
        pause
        exit /b 1
    )
    echo        Frontend dependencies installed.
) else (
    echo        Frontend dependencies already installed.
)

:: -------------------------------------------
:: Step 5: Setup config if needed
:: -------------------------------------------
echo  [5/6] Checking configuration...
cd /d "%~dp0"

if not exist "config\credentials.py" (
    echo        Creating credentials file from template...
    copy "config\credentials.example.py" "config\credentials.py" >nul 2>&1
    echo        [NOTE] Edit config\credentials.py with your API credentials if needed.
) else (
    echo        Configuration already exists.
)

:: Create required directories
if not exist "logs" mkdir logs
if not exist "token_backups" mkdir token_backups
if not exist "data" mkdir data
echo        Directories ready.

:: -------------------------------------------
:: Step 6: Launch the application
:: -------------------------------------------
echo  [6/6] Launching Trading Dashboard...
echo.
echo  ============================================================
echo     STARTING SERVERS
echo  ============================================================
echo.

:: Kill any existing processes on our ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Start backend server
echo  Starting backend server on http://localhost:8000 ...
cd /d "%~dp0web_dashboard\backend"
start "GT Trading - Backend" cmd /k "color 0B && echo [Backend Server] Starting... && python main.py"

:: Wait for backend to initialize
echo  Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

:: Start frontend server
echo  Starting frontend server on http://localhost:3000 ...
cd /d "%~dp0web_dashboard\frontend"
start "GT Trading - Frontend" cmd /k "color 0E && echo [Frontend Server] Starting... && npm start"

:: Wait for frontend to compile
echo  Waiting for frontend to compile...
timeout /t 15 /nobreak >nul

:: Open browser
echo  Opening browser...
start http://localhost:3000

echo.
echo  ============================================================
echo     SETUP COMPLETE - DASHBOARD IS RUNNING!
echo  ============================================================
echo.
echo    Backend:   http://localhost:8000
echo    Frontend:  http://localhost:3000
echo    Dashboard: http://localhost:3000 (opens automatically)
echo.
echo    Two new windows opened:
echo      - Backend Server (blue title)
echo      - Frontend Server (yellow title)
echo.
echo    To STOP: Close both server windows, or press Ctrl+C in each.
echo    To RESTART: Double-click run.bat (skips dependency install).
echo.
echo  ============================================================
echo.
pause
