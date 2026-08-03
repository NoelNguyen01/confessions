@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   CONFESSION - ngrok tunnel (public URL)
echo ============================================
echo.
echo Make sure run.bat is running in another window first.
echo Then copy the https://xxxx.ngrok-free.dev URL from here
echo and paste it into your Apps Script.
echo.
echo Download ngrok from https://ngrok.com/download
echo then put ngrok.exe in this folder or in PATH.
echo.

set /p PORT=Port to tunnel (default 3000): 
if "%PORT%"=="" set PORT=3000

where ngrok >nul 2>nul
if errorlevel 1 (
    echo ngrok.exe not found in PATH.
    if exist "%~dp0ngrok.exe" (
        "%~dp0ngrok.exe" http %PORT%
    ) else (
        echo Put ngrok.exe next to this .bat file or add it to PATH.
        pause
    )
) else (
    ngrok http %PORT%
)
