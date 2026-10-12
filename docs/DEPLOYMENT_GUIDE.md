# DEPLOYMENT_GUIDE.md — Raspberry Pi 5 Step-by-Step Installation & Commissioning

> **Target Platform**: Raspberry Pi 5 (4GB / 8GB RAM)
> **Operating System**: Raspberry Pi OS 64-bit (Debian Bookworm) or Ubuntu Server 24.04 LTS (64-bit)
> **Controller**: Selec MiBRX-6M PLC via Modbus TCP

---

## 1. System Update & Base Packages

Log into the Raspberry Pi 5 terminal via SSH or direct console:

```bash
# Update package repositories and system libraries
sudo apt update && sudo apt upgrade -y

# Install build essentials, Python 3, venv, git, curl, and I2C/SPI utilities
sudo apt install -y python3 python3-pip python3-venv git curl ufw i2c-tools libatlas-base-dev
```

---

## 2. Dedicated Application User & Group

Isolate the service under an unprivileged system user with access to hardware peripheral groups (`i2c`, `spi`, `dialout`):

```bash
# Create system user 'iotgateway' without login shell
sudo useradd -r -s /bin/false -d /opt/selec-iot-dashboard -m iotgateway

# Grant hardware bus permissions to iotgateway
sudo usermod -aG i2c,spi,dialout iotgateway
```

---

## 3. Clone / Deploy Application Code

Place the project files into `/opt/selec-iot-dashboard`:

```bash
# Set directory permissions
sudo mkdir -p /opt/selec-iot-dashboard
sudo chown -R $USER:$USER /opt/selec-iot-dashboard

# Copy or clone repo into the directory
cd /opt/selec-iot-dashboard
# (Copy files into /opt/selec-iot-dashboard)
```

---

## 4. Install Node.js & Build Frontend Dashboard

```bash
# Install Node.js LTS (v20 or v22)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Navigate to frontend and build production bundle
cd /opt/selec-iot-dashboard/frontend
npm ci
npm run build
```

This compiles optimized client bundles into `/opt/selec-iot-dashboard/frontend/dist`.

---

## 5. Python Virtual Environment & Backend Dependencies

```bash
cd /opt/selec-iot-dashboard

# Create virtual environment
python3 -m venv venv

# Upgrade pip and install pinned backend dependencies
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r backend/requirements.txt
```

---

## 6. Configure Environment & Register Map

```bash
# Copy environment configuration
cp .env.example .env

# Edit .env for production parameters
nano .env
```

Ensure the following keys are set:
- `PLC_HOST`: IP address of the Selec MiBRX-6M PLC (e.g. `192.168.1.50`)
- `PLC_PORT`: `502` for physical PLC, or `5020` for local simulation
- `SIMULATION_MODE`: `false` for physical PLC, `true` for offline simulation
- `ALLOW_REMOTE_CONTROL`: `false` (default: disabled for safety)
- `VIBRATION_SENSOR_INTERFACE`: `I2C_ADXL345` (if using physical ADXL345 on GPIO pins) or `MOCK`

Review `config/register_map.yaml` to ensure register addresses match the Selec Ladder configuration.

---

## 7. Run Verification Test Suite

Run the automated test suite to confirm all decoders, latency percentiles, and safety controls function:

```bash
./venv/bin/python -m pytest
```

---

## 8. Run Safe Read-Only Modbus Diagnostic Tool

Before starting continuous service, verify connectivity with the PLC:

```bash
./venv/bin/python tools/modbus_test.py --host 192.168.1.50 --port 502 --unit 1
```

Confirm that Discrete Inputs and Holding Registers read without Modbus exception errors.

---

## 9. Run Latency Benchmark Profiler

Run a 15-second benchmark to verify communication round-trip times:

```bash
./venv/bin/python tools/latency_benchmark.py --duration 15 --out data/benchmark_precommission.csv
```

---

## 10. Install & Enable systemd Service

Set directory ownership to `iotgateway`:

```bash
sudo chown -R iotgateway:iotgateway /opt/selec-iot-dashboard

# Install systemd service unit
sudo cp deploy/systemd/selec-iot.service /etc/systemd/system/

# Reload daemon, enable auto-start, and start service
sudo systemctl daemon-reload
sudo systemctl enable selec-iot
sudo systemctl start selec-iot
```

Verify service status:

```bash
sudo systemctl status selec-iot
```

View live operational logs:

```bash
sudo journalctl -u selec-iot -f
```

---

## 11. Network Security & Firewall (UFW)

Restrict incoming access to authorized engineering workstations:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8000/tcp comment 'Selec IIoT Dashboard'
sudo ufw enable
```

Access the dashboard in your web browser at:
`http://<raspberry-pi-ip>:8000`

---

## 12. Backup & Disaster Recovery Procedures

To back up the application database and configuration:

```bash
# Safe backup of SQLite database while service is running
sqlite3 /opt/selec-iot-dashboard/data/selec_iot.db ".backup /opt/selec-iot-dashboard/data/backup_$(date +%Y%m%d_%H%M%S).db"

# Backup configuration files
tar -czvf /opt/backup_config_$(date +%Y%m%d).tar.gz /opt/selec-iot-dashboard/.env /opt/selec-iot-dashboard/config/
```

To restore from backup:

```bash
sudo systemctl stop selec-iot
cp /path/to/backup.db /opt/selec-iot-dashboard/data/selec_iot.db
sudo chown iotgateway:iotgateway /opt/selec-iot-dashboard/data/selec_iot.db
sudo systemctl start selec-iot
```
