#!/usr/bin/env bash
# ==============================================================================
# Selec MiBRX-6M SCADA Live Dashboard Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "    Selec PLC SCADA Live Dashboard Launcher                           "
echo "======================================================================"

# Locate or create Linux virtual environment (venv)
if [ ! -f "$SCRIPT_DIR/venv/bin/python" ]; then
    echo "[*] Initializing Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    "$SCRIPT_DIR/venv/bin/pip" install --upgrade pip
    if [ -f "$SCRIPT_DIR/backend/requirements.txt" ]; then
        "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/backend/requirements.txt"
    else
        "$SCRIPT_DIR/venv/bin/pip" install fastapi uvicorn pymodbus
    fi
fi

PYTHON_EXEC="$SCRIPT_DIR/venv/bin/python"

# Verify fastapi is installed in venv
if ! "$PYTHON_EXEC" -c "import fastapi, uvicorn, pymodbus" >/dev/null 2>&1; then
    echo "[*] Installing required packages into venv (fastapi, uvicorn, pymodbus)..."
    "$SCRIPT_DIR/venv/bin/pip" install fastapi uvicorn pymodbus
fi

PORT="${PORT:-8080}"
echo "Launching SCADA Dashboard on port $PORT..."
echo "Open your browser to: http://localhost:$PORT"
echo "Target PLC: 192.168.1.50:502 (Modbus Unit ID: 1)"
echo "Press Ctrl+C to stop."
echo "======================================================================"

# Auto-open browser in background if on desktop
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    if command -v xdg-open >/dev/null 2>&1; then
        (sleep 2 && xdg-open "http://localhost:$PORT" >/dev/null 2>&1) &
    fi
fi

exec $PYTHON_EXEC simple_dashboard.py
