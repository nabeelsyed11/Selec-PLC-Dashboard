@echo off
REM ==============================================================================
REM Selec MiBRX-6M PLC Dashboard - One-Click Start Script for Windows
REM ==============================================================================

setlocal enabledelayedexpansion
title Selec PLC Dashboard - Industrial IoT Edge Server

cd /d "%~dp0"

echo ======================================================================
echo     Selec MiBRX-6M Industrial IoT Edge Gateway ^& Live Dashboard       
echo ======================================================================
echo.

REM 1. Check Python
echo [1/5] Checking Python environment...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)
python -c "import sys; print('      Python found: ' + sys.version.split()[0])"

REM 2. Check and copy .env
echo [2/5] Checking configuration (.env)...
if not exist ".env" (
    if exist ".env.example" (
        echo       .env not found. Creating default .env from .env.example...
        copy .env.example .env >nul
        echo       [OK] .env initialized.
    )
) else (
    echo       [OK] .env configuration detected.
)

if not exist "data" mkdir data

REM 3. Virtual Environment Check & Setup (clean up Linux/Pi-copied venv if present)
echo [3/5] Verifying Python virtual environment (venv)...
if exist "venv" (
    if not exist "venv\Scripts\python.exe" (
        echo       Detected non-Windows or corrupted virtual environment.
        echo       Cleaning and recreating Windows venv...
        rd /s /q venv
    )
)

if not exist "venv\Scripts\python.exe" (
    echo       Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo       [OK] Virtual environment verified.

REM 4. Dependencies Check
echo [4/5] Checking dependencies...
venv\Scripts\python -c "import fastapi, uvicorn, pymodbus, pydantic_settings, aiosqlite, sqlalchemy, yaml, numpy, scipy, psutil" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo       Installing dependencies from backend\requirements.txt...
    venv\Scripts\python -m pip install --upgrade pip --quiet
    venv\Scripts\pip install -r backend\requirements.txt
    echo       [OK] Dependencies installed.
) else (
    echo       [OK] Dependencies ready.
)

REM 5. Check UI
echo [5/5] Checking frontend bundle...
if exist "frontend\dist\index.html" (
    echo       [OK] Pre-compiled React dashboard verified [frontend\dist].
) else (
    echo       [WARNING] Pre-compiled frontend not found in frontend\dist!
)

REM Check if port 8000 is already in use
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo.
    echo [WARNING] Port 8000 appears to be in use by another application.
    echo If another dashboard instance is already running, please close it first.
    echo.
)

echo.
echo ======================================================================
echo        SYSTEM READY! Starting Selec PLC Dashboard Server...          
echo ======================================================================
echo   * Local URL:        http://localhost:8000
echo   * REST API ^& Docs:  http://localhost:8000/docs
echo   * Stop Server:      Press Ctrl + C
echo ======================================================================
echo.

REM Automatically open default browser after brief delay
start "" http://localhost:8000

REM Run the Uvicorn server with backend app directory
venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

echo.
echo Dashboard server stopped.
pause
