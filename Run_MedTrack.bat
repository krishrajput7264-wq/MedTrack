@echo off
title MedTrack Cloud Healthcare Management System
echo ================================================================
echo    Starting MedTrack Cloud Healthcare Management System
echo ================================================================
echo.

cd /d "%~dp0"

:: Check if port 5000 is already active
netstat -ano | findstr :5000 >nul
if %errorlevel% equ 0 (
    echo [INFO] MedTrack server is already running on port 5000.
) else (
    echo [INFO] Starting Flask server...
    start /B python app.py
    timeout /t 2 /nobreak >nul
)

echo [INFO] Opening MedTrack Web Application in your browser...
start http://127.0.0.1:5000/

echo.
echo ================================================================
echo MedTrack is LIVE at: http://127.0.0.1:5000/
echo.
echo Demo Logins:
echo   * Patient: alex.mercer@gmail.com  (Password: patient123)
echo   * Doctor:  sarah.mitchell@medtrack.org (Password: doctor123)
echo ================================================================
echo.
echo Press any key to close this console.
pause >nul
