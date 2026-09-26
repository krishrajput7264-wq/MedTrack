@echo off
title MedTrack Cloud Healthcare System
echo Starting MedTrack Cloud Healthcare System...

cd /d "C:\Users\Pansa\OneDrive\Desktop\MedTrack"

:: Check if server is running on port 5000
netstat -ano | findstr :5000 >nul
if %errorlevel% neq 0 (
    echo Launching background server...
    start /B python app.py
    timeout /t 2 /nobreak >nul
)

echo Opening MedTrack in your browser...
start http://127.0.0.1:5000/
exit
