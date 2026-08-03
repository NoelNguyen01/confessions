@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   CONFESSION - Setup for Windows 10
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment (.venv) ...
    python -m venv .venv
    if errorlevel 1 (
        echo FAILED: Python not found. Install Python 3.8+ from https://python.org
        echo and tick "Add Python to PATH" during install.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists.
)

echo [2/4] Installing dependencies ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo FAILED: cannot install dependencies.
    pause
    exit /b 1
)

echo [3/4] Checking .env file ...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example
    echo IMPORTANT: Open .env and fill in your real values!
) else (
    echo .env already exists.
)

echo [4/4] Checking credentials.json ...
if exist "credentials.json" (
    echo credentials.json found. Good.
) else (
    echo.
    echo WARNING: credentials.json NOT found.
    echo Create the Service Account key (see README section 6) and save it here
    echo as credentials.json, in the SAME folder as run.py.
)

echo.
echo Setup complete. Open .env to configure, then run "run.bat"
pause
