# Raspberry Pi 4B Deployment Guide for Selec PLC Dashboard

## Prerequisites on Pi
- Raspberry Pi 4B (4GB/8GB recommended)
- Raspberry Pi OS 64-bit (Bookworm or newer)
- MicroSD card 32GB+ Class 10
- Ethernet cable for PLC connection

## Network Architecture Options

### Option A: Direct Ethernet to PLC (Recommended for Industrial)
```
[PLC] ----Ethernet cable---- [Pi eth0] ----WiFi/Ethernet---- [Your Laptop Browser]
```
- Pi acts as gateway
- PLC on Pi's eth0 subnet (e.g., 192.168.1.x)
- Pi WiFi connects to your network for remote access

### Option B: Both on Same Network Switch
```
[PLC] ----Switch---- [Pi] ----Switch---- [Your Laptop]
```
- PLC and Pi on same LAN
- Router assigns IPs via DHCP

---

## Step-by-Step Pi Setup

### 1. Flash Pi OS
```bash
# On your laptop - use Raspberry Pi Imager
# Select: Raspberry Pi OS (64-bit) Lite or Desktop
# Enable: SSH, WiFi, set hostname, user/password
```

### 2. Initial Pi Config (via SSH)
```bash
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-venv python3-pip git \
    libopenblas-dev build-essential \
    sqlite3

# Clone your project
git clone <your-repo-url> selec-dashboard
cd selec-dashboard
```

### 3. Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 4. Network Config for PLC

#### If PLC is on 192.168.1.50 (direct connect):
```bash
# Edit Pi's eth0 for static IP
sudo nano /etc/dhcpcd.conf

# Add:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 1.1.1.1
```

Then reboot: `sudo reboot`

### 5. Update .env for Pi
```bash
cd ~/selec-dashboard
cp .env.example .env
nano .env
```
Key changes:
```env
PLC_HOST=192.168.1.50    # Your PLC IP
PLC_PORT=502
PLC_UNIT_ID=1
SIMULATION_MODE=false    # Use real PLC!
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 6. Build Frontend (on Pi or laptop then copy)
```bash
# On laptop with Node.js
cd frontend
npm install
npm run build
# Copy dist/ to Pi's frontend/dist/
```

### 7. Systemd Service for Auto-Start
```bash
sudo nano /etc/systemd/system/selec-dashboard.service
```
```ini
[Unit]
Description=Selec MiBRX-6M PLC Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/selec-dashboard
ExecStart=/home/pi/selec-dashboard/venv/bin/python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable selec-dashboard
sudo systemctl start selec-dashboard
```

### 8. Verify
```bash
# Check logs
sudo journalctl -u selec-dashboard -f

# Test locally
curl http://localhost:8000/api/system/config

# From laptop
http://raspberrypi.local:8000
```

---

## Firewall / Security
```bash
# Allow only LAN access
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw allow from 192.168.31.0/24 to any port 8000  # Your WiFi subnet
sudo ufw enable
```

---

## Troubleshooting Pi Common Issues

| Issue | Fix |
|-------|-----|
| `pymodbus` import fails | `pip install --upgrade pymodbus` |
| Frontend shows blank | Check `frontend/dist/` exists, rebuild |
| DB locked | Check `data/` folder permissions |
| Port 8000 in use | `sudo lsof -i:8000` then kill |

---

## Performance Tips for Pi 4B
- Use `uvicorn --workers 1` (single process for WebSocket)
- Enable SQLite WAL mode (already in code)
- Mount `/data` on tmpfs for SD card longevity:
  ```bash
  sudo nano /etc/fstab
  # Add: tmpfs /home/pi/selec-dashboard/data tmpfs defaults,noatime,nosuid,size=100M 0 0
  ```

---

## Quick Test Checklist Before Production
- [ ] Pi boots and gets IP
- [ ] Can ping PLC IP from Pi
- [ ] Modbus test script passes: `python tools/test_plc_connectivity.py`
- [ ] Dashboard loads in browser
- [ ] WebSocket connects (green indicator)
- [ ] Service auto-starts on reboot