@echo off
setlocal
echo ======================================================================
echo     Selec PLC IW0 (Address 40768) Simple Live Dashboard
echo ======================================================================

set PORT=8080
echo Launching Simple Dashboard on port %PORT%...
echo Open your browser to: http://localhost:%PORT%
echo Target PLC: 192.168.1.50:502 (Modbus Unit ID: 1)
echo Press Ctrl+C to stop.
echo ======================================================================

python simple_dashboard.py
pause
