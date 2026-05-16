@echo off
setlocal enabledelayedexpansion
title GT Trading Companion - Quick Start
color 0A

echo.
echo  ============================================================
echo     GT TRADING COMPANION - QUICK START
echo  ============================================================
echo.
echo  Starting servers (dependencies already installed)...
echo.

:: Kill any existing processes on our ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Start backend
echo  Starting backend on http://localhost:8000 ...
cd /d "%~dp0web_dashboard\backend"
start "GT Trading - Backend" cmd /k "color 0B && echo [Backend Server] Starting... && python main.py"

:: Wait for backend
timeout /t 5 /nobreak >nul

:: Start frontend
echo  Starting frontend on http://localhost:3000 ...
cd /d "%~dp0web_dashboard\frontend"
start "GT Trading - Frontend" cmd /k "color 0E && echo [Frontend Server] Starting... && npm start"

:: Wait for frontend
timeout /t 15 /nobreak >nul

:: Open browser
start http://localhost:3000

echo.
echo  Dashboard is running!
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:3000
echo.
echo  Close the server windows to stop.
echo.
pause
