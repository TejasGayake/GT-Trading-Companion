@echo off
echo ========================================
echo    TRADING DASHBOARD - ONE CLICK START
echo ========================================
echo.

echo [0/4] Checking for existing processes...

:: Kill existing backend on port 8000
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %a >nul 2>&1
)

:: Kill existing node processes for frontend
taskkill /F /IM node.exe >nul 2>&1

timeout /t 2 /nobreak >nul

echo [1/4] Starting Backend Server...
cd /d "%~dp0backend"
start "Trading Dashboard Backend" cmd /k "python main.py"

echo [2/4] Starting Frontend Server...
cd /d "%~dp0frontend"
start "Trading Dashboard Frontend" cmd /k "npm start"

echo [3/4] Waiting for servers to start...
timeout /t 12 /nobreak >nul

echo [4/4] Opening Browser...
start http://localhost:3000

echo.
echo ========================================
echo    Dashboard is opening in browser!
echo    Backend running on http://localhost:8000
echo    Frontend running on http://localhost:3000
echo ========================================
echo.
echo Press any key to close this window...
pause >nul