#!/usr/bin/env bash
# ==============================================================================
# Selec MiBRX-6M IW0 (Address 40768) Simple Live Dashboard Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "    Selec PLC IW0 (Address 40768) Simple Live Dashboard              "
echo "======================================================================"

if [ -f "venv/bin/python" ]; then
    PYTHON_EXEC="./venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_EXEC="python3"
else
    echo "[ERROR] Python not found!"
    exit 1
fi

PORT="${PORT:-8080}"
echo "Launching Simple Dashboard on port $PORT..."
echo "Open your browser to: http://localhost:$PORT"
echo "Target PLC: 192.168.1.50:502 (Modbus Unit ID: 1)"
echo "Press Ctrl+C to stop."
echo "======================================================================"

exec $PYTHON_EXEC simple_dashboard.py
