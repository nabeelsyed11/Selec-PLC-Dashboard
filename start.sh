#!/usr/bin/env bash
# ==============================================================================
# Selec MiBRX-6M PLC Dashboard - One-Click Start Script
# Works on: Raspberry Pi 4B / 5 / Raspberry Pi OS / Ubuntu / Debian / Linux
# ==============================================================================

set -e

# Change directory to the project root regardless of where script is called
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$SCRIPT_DIR"

# ANSI Colors for Industrial Console
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Trap errors so the terminal window NEVER closes automatically on failure
pause_on_exit() {
    local code=$?
    # Exit codes 0, 130 (SIGINT / Ctrl+C), and 143 (SIGTERM) are normal terminations
    if [ $code -ne 0 ] && [ $code -ne 130 ] && [ $code -ne 143 ]; then
        echo ""
        echo -e "${RED}${BOLD}[ERROR] Script stopped with exit code $code.${NC}"
        echo "Check the error messages above to resolve the issue."
        echo ""
        read -r -p "Press Enter to close this window..." dummy || true
    fi
}
trap pause_on_exit EXIT

echo -e "${CYAN}${BOLD}"
echo "======================================================================"
echo "    Selec MiBRX-6M Industrial IoT Edge Gateway & Live Dashboard       "
echo "======================================================================"
echo -e "${NC}"

# 1. Check Python 3 Availability
echo -e "${BLUE}[1/5] Checking Python environment...${NC}"
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo -e "${RED}[ERROR] Python 3 was not found! Please install it with:${NC}"
    echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    read -r -p "Press Enter to close..." dummy || true
    exit 1
fi

PY_VER=$($PY_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "      Found Python ${GREEN}${PY_VER}${NC} via ${PY_BIN}"

# 2. Check and Prepare .env Configuration File
echo -e "${BLUE}[2/5] Checking configuration (.env)...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "      ${YELLOW}.env not found. Creating default .env from .env.example...${NC}"
        cp .env.example .env
        echo -e "      ${GREEN}[OK] .env initialized.${NC}"
    else
        echo -e "      ${RED}[WARNING] Neither .env nor .env.example found! Using built-in defaults.${NC}"
    fi
else
    # Auto-migrate any obsolete MOCK setting to GPIO_DIGITAL on physical hardware
    sed -i 's/^VIBRATION_SENSOR_INTERFACE=MOCK/VIBRATION_SENSOR_INTERFACE=GPIO_DIGITAL/' .env 2>/dev/null || true
    echo -e "      ${GREEN}[OK] .env configuration detected (Vibration: GPIO_DIGITAL on Pin 11).${NC}"
fi

# Ensure data directory exists for SQLite & CSV logs
mkdir -p data

# 3. Virtual Environment Check & Auto-Creation (with Windows-cross-copy detection)
echo -e "${BLUE}[3/5] Verifying Linux Python virtual environment (venv)...${NC}"
if [ -d "venv" ]; then
    # Detect Windows-copied virtual environment (contains Windows Scripts/ and .exe files)
    if [ -d "venv/Scripts" ] || [ ! -f "venv/bin/python" ] || [ ! -f "venv/bin/pip" ]; then
        echo -e "      ${YELLOW}Detected Windows-copied venv folder (contains Windows .exe files).${NC}"
        echo -e "      ${YELLOW}Removing Windows venv and building a native Linux ARM environment...${NC}"
        rm -rf venv
    fi
fi

if [ ! -d "venv" ]; then
    echo -e "      ${YELLOW}Creating fresh Linux virtual environment (venv)...${NC}"
    if ! $PY_BIN -m venv venv 2>/dev/null; then
        echo ""
        echo -e "${RED}${BOLD}[ERROR] Failed to create virtual environment!${NC}"
        echo -e "${YELLOW}Raspberry Pi OS requires 'python3-venv'. Please run this command:${NC}"
        echo ""
        echo -e "    ${BOLD}sudo apt update && sudo apt install -y python3-venv python3-pip libopenblas-dev${NC}"
        echo ""
        read -r -p "Press Enter to close..." dummy || true
        exit 1
    fi
    echo -e "      ${GREEN}[OK] Fresh Linux venv created.${NC}"
fi

# 4. Install / Verify Python Dependencies
echo -e "${BLUE}[4/5] Checking backend dependencies...${NC}"
NEED_INSTALL=false

if ! ./venv/bin/python -c "import fastapi, uvicorn, pymodbus, pydantic_settings, aiosqlite, sqlalchemy, yaml, numpy, scipy, psutil" >/dev/null 2>&1; then
    NEED_INSTALL=true
fi

if [ "$NEED_INSTALL" = true ]; then
    echo -e "      ${YELLOW}Installing required Python packages (this may take a few minutes on first run)...${NC}"
    ./venv/bin/python -m pip install --upgrade pip
    if ! ./venv/bin/pip install -r backend/requirements.txt; then
        echo ""
        echo -e "${RED}${BOLD}[ERROR] Failed to install Python dependencies!${NC}"
        echo -e "${YELLOW}If installation failed due to C-compilation, run:${NC}"
        echo -e "    ${BOLD}sudo apt install -y build-essential libopenblas-dev${NC}"
        echo ""
        read -r -p "Press Enter to close..." dummy || true
        exit 1
    fi
    echo -e "      ${GREEN}[OK] Dependencies successfully installed.${NC}"
else
    echo -e "      ${GREEN}[OK] All dependencies (FastAPI, PyModbus, Uvicorn, etc.) are ready.${NC}"
fi

# 5. Check UI Bundle
echo -e "${BLUE}[5/5] Checking frontend bundle...${NC}"
if [ -f "frontend/dist/index.html" ]; then
    echo -e "      ${GREEN}[OK] Pre-compiled React dashboard verified (frontend/dist).${NC}"
else
    echo -e "      ${YELLOW}[WARNING] frontend/dist/index.html not found!${NC}"
fi

# Check if port 8000 is already occupied
if command -v ss >/dev/null 2>&1; then
    if ss -tuln 2>/dev/null | grep -q ":8000 "; then
        echo ""
        echo -e "${YELLOW}[WARNING] Port 8000 is already in use by another process!${NC}"
        echo -e "${YELLOW}If a previous dashboard or service is running, stop it first:${NC}"
        echo -e "    ${BOLD}sudo kill -9 \$(sudo lsof -t -i:8000 2>/dev/null)${NC}"
        echo ""
    fi
fi

# Determine Local Network IP for convenient operator access
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi

# If on Raspberry Pi desktop GUI, open browser in background after server boots
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    if command -v xdg-open >/dev/null 2>&1; then
        (sleep 2 && xdg-open "http://localhost:8000" >/dev/null 2>&1) &
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}======================================================================${NC}"
echo -e "${GREEN}${BOLD}       SYSTEM READY! Starting Selec PLC Dashboard Server...          ${NC}"
echo -e "${GREEN}${BOLD}======================================================================${NC}"
echo -e "  * Local Access:     ${CYAN}http://localhost:8000${NC}"
echo -e "  * Network Access:   ${CYAN}http://${LOCAL_IP}:8000${NC}"
echo -e "  * REST API & Docs:  ${CYAN}http://${LOCAL_IP}:8000/docs${NC}"
echo -e "  * Stop Server:      ${YELLOW}Press Ctrl + C${NC}"
echo -e "${GREEN}${BOLD}======================================================================${NC}"
echo ""

# Disable errexit before running server so Ctrl+C (code 130) is handled gracefully
set +e

# Run Uvicorn directly (WITHOUT exec so the terminal stays open if it exits)
./venv/bin/python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
SERVER_EXIT_CODE=$?

if [ $SERVER_EXIT_CODE -ne 0 ] && [ $SERVER_EXIT_CODE -ne 130 ] && [ $SERVER_EXIT_CODE -ne 143 ]; then
    echo ""
    echo -e "${RED}[ERROR] Server stopped with error code $SERVER_EXIT_CODE.${NC}"
else
    echo ""
    echo -e "${GREEN}Dashboard server stopped cleanly.${NC}"
fi

echo ""
read -r -p "Press Enter to close this window..." dummy || true
