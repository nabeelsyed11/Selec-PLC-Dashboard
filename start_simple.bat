@echo off
setlocal
echo ======================================================================
echo     Selec PLC SCADA Live Dashboard Launcher
echo ======================================================================

set PORT=8080
echo Launching SCADA Dashboard on port %PORT%...
echo Open your browser to: http://localhost:%PORT%
echo Target PLC: 192.168.1.50:502 (Modbus Unit ID: 1)
echo Press Ctrl+C to stop.
echo ======================================================================

start "" http://localhost:%PORT%

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe simple_dashboard.py
) else (
    python simple_dashboard.py
)
pause
