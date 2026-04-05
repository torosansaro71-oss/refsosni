@echo off
title Roblox Cookie Refresher
cd /d "%~dp0"

echo ========================================
echo   Roblox Cookie Refresher
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies
echo [*] Installing dependencies...
pip install -r requirements.txt --quiet 2>nul
echo [OK] Dependencies installed
echo.

:: Start server
echo [*] Starting server on http://127.0.0.1:5000
echo [*] Open your browser and go to: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

start "" "http://127.0.0.1:5000"
python server.py
