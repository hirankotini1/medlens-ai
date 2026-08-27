@echo off
title MEDLENS AI - Clinical Pathology Platform
color 0B

echo ======================================================================
echo                     MEDLENS AI CLINICAL PLATFORM
echo ======================================================================
echo.
echo [1/3] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH! Please install Python 3.9+.
    pause
    exit /b
)

echo [2/3] Starting backend server on http://127.0.0.1:8000 ...
cd /d "%~dp0"

:: Launch default web browser after 2 seconds
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000/"

echo [3/3] Platform is LIVE! (Keep this window open while using the website)
echo ----------------------------------------------------------------------
echo Access URL : http://127.0.0.1:8000
echo API Docs   : http://127.0.0.1:8000/docs
echo ----------------------------------------------------------------------
echo.

python -m uvicorn disease_prediction.api.main:app --host 127.0.0.1 --port 8000
pause
