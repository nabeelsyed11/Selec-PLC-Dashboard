#!/usr/bin/env bash
# ==============================================================================
# Selec MiBRX-6M PLC Dashboard - One-Click Start Script
# Works on: Raspberry Pi 5 / Raspberry Pi OS / Ubuntu / Debian / Linux ARM64 & x86
# ==============================================================================

set -e

# Change directory to the project root regardless of where script is called
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ANSI Colors for Industrial Console
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "======================================================================"
echo "    Selec MiBRX-6M Industrial IoT Edge Gateway & Live Dashboard       "
echo "======================================================================"
echo -e "${NC}"

# 1. Check Python 3 Availability
echo -e "${BLUE}[1/5] Checking Python environment...${NC}"
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo -e "${RED}[ERROR] Python 3 was not found! Please install it with:${NC}"
    echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
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
    echo -e "      ${GREEN}[OK] .env configuration detected.${NC}"
fi

# Ensure data directory exists for SQLite & CSV logs
mkdir -p data

# 3. Virtual Environment Check & Auto-Creation (with Windows-cross-copy detection)
echo -e "${BLUE}[3/5] Verifying Linux Python virtual environment (venv)...${NC}"
RECREATE_VENV=false

if [ ! -d "venv" ]; then
    echo -e "      ${YELLOW}venv directory not found. Creating new virtual environment...${NC}"
    RECREATE_VENV=true
elif [ ! -f "venv/bin/python" ] || [ ! -f "venv/bin/pip" ]; then
    echo -e "      ${YELLOW}Detected incompatible or Windows-copied venv folder.${NC}"
    echo -e "      ${YELLOW}Removing old venv and rebuilding a native Linux environment...${NC}"
    rm -rf venv
    RECREATE_VENV=true
fi

if [ "$RECREATE_VENV" = true ]; then
    $PY_BIN -m venv venv || {
        echo -e "${RED}[ERROR] Failed to create venv. You may need python3-venv:${NC}"
        echo "  sudo apt update && sudo apt install -y python3-venv"
        exit 1
    }
    echo -e "      ${GREEN}[OK] Fresh Linux venv created.${NC}"
fi

# 4. Install / Verify Python Dependencies
echo -e "${BLUE}[4/5] Checking backend dependencies...${NC}"
NEED_INSTALL=false

# Quick check if core libraries are installed
if ! ./venv/bin/python -c "import fastapi, uvicorn, pymodbus" &>/dev/null; then
    NEED_INSTALL=true
fi

if [ "$NEED_INSTALL" = true ]; then
    echo -e "      ${YELLOW}Installing required Python packages from backend/requirements.txt...${NC}"
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r backend/requirements.txt
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
    if command -v npm &>/dev/null; then
        echo -e "      Building frontend with npm..."
        cd frontend && npm install && npm run build && cd ..
    else
        echo -e "      ${RED}Warning: Frontend assets missing. Backend API will run on /api and /docs.${NC}"
    fi
fi

# Determine Local Network IP for convenient operator access
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
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

# Hand over process control to Uvicorn for clean signal handling (SIGINT/SIGTERM)
exec ./venv/bin/python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
