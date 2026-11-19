@echo off
REM Selec PLC Dashboard - Simulation Mode Launcher
cd /d "%~dp0"

echo ======================================================================
echo     Selec MiBRX-6M Industrial IoT Gateway - SIMULATION Mode
echo ======================================================================
echo.
echo This mode runs with MOCK PLC data. No physical hardware required.
echo.

REM Stop any existing instance
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo Starting server with SIMULATION_MODE=true...
echo PLC will be simulated with realistic industrial data.
echo.

start "" http://localhost:8000

REM Run uvicorn with simulation mode environment
set SIMULATION_MODE=true
set PLC_HOST=127.0.0.1
set PLC_PORT=5020
venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

pause