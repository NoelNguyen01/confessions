@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No virtual environment found. Run setup.bat first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo No .env found. Run setup.bat first (or copy .env.example to .env).
    pause
    exit /b 1
)

echo Starting CONFESSION server ...
echo URL for Apps Script: http://localhost:3000/submit/YOUR_KEY
echo (Replace YOUR_KEY with the value in your .env)
echo Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" run.py

echo.
echo Server stopped.
pause
