# Selec MiBRX-6M Industrial IoT Edge Gateway & Live Dashboard

An industrial-grade Edge IoT monitoring, latency benchmarking, and machine control dashboard for the **Selec MiBRX-6M PLC** paired with a **Raspberry Pi 5** and direct vibration sensing.

---

## ⚡ Quick Start (One Command)

### On Raspberry Pi 5 / Linux:
```bash
git clone https://github.com/nabeelsyed11/Selec-PLC-Dashboard.git
cd Selec-PLC-Dashboard
./start.sh
```

### On Windows:
Double-click `start.bat` or run in PowerShell / Command Prompt:
```cmd
start.bat
```

> **What the start script does automatically:**
> 1. Verifies Python 3 installation.
> 2. Auto-initializes `.env` from template if not present.
> 3. Detects and auto-creates the virtual environment (`venv`). *(If files were copied from Windows to Pi, it safely rebuilds a native Linux venv).*
> 4. Installs required Python dependencies (`FastAPI`, `PyModbus`, `Uvicorn`, `SciPy`, etc.).
> 5. Detects Pi local IP address and launches the server on `http://0.0.0.0:8000`.

---

## 🌐 Accessing the Dashboard

Once started, open your web browser:
* **On the Raspberry Pi itself:** [http://localhost:8000](http://localhost:8000)
* **From any phone, tablet, or PC on the same Wi-Fi/LAN:** `http://<YOUR_PI_IP>:8000`
* **Interactive API Documentation (Swagger):** `http://<YOUR_PI_IP>:8000/docs`

> *Note: Pre-compiled React production assets are included in `frontend/dist`. You do **NOT** need to install Node.js or `npm` on the Raspberry Pi 5!*

---

## 🏭 Connected Sensors & Modbus TCP Signals

| Equipment / Sensor | MiBRX-6M IO / Protocol | Modbus Register | Processing & Logic |
| :--- | :--- | :--- | :--- |
| **Load Cell** | Analog Input (0–10V / 4–20mA) | `40001` (Holding Reg) | Live tare zeroing, span calibration factor ($kg$) |
| **Motor Temperature** | RTD / PT100 Module | `40002` (Holding Reg) | 0.1 °C scaling, warning (75 °C) & critical alarms (90 °C) |
| **Belt Slip Detector** | Proximity on driven roller | `10001` (Discrete Input) | Debounced state, mismatch detection vs VFD running status |
| **High-Speed Encoder**| High-Speed Counter (HSC) | `40003–40004` (32-bit UINT) | Rollover compensation ($2^{32}-1$), line speed ($m/min$) |
| **Energy Meter** | RS-485 to MiBRX Gateway | `40010–40020` (Float32) | Voltage, Current, Active Power (kW), Power Factor, Energy (kWh) |
| **Optical Counter** | High-Speed Digital Input | `40005–40006` (32-bit UINT) | Unit count, batches, current parts-per-minute (PPM) rate |
| **Pusher Actuator** | Digital Output + Feedback DI | `00001` (Coil) / `10002` (DI) | Safe control handshake, travel timeout & jam detection |
| **VFD Interface** | Analog Out (Speed) + DI/DO | `40007` (Freq) / `00002` (Run) | Speed reference (0–50 Hz), run/trip feedback & current |
| **Vibration Sensor** | Direct Raspberry Pi 5 GPIO | I2C / SPI / Mock engine | 1000 Hz decoupled sampling, RMS velocity, 512-pt FFT spectrum |

---

## ⏱️ Latency Measurement Engine

The dashboard strictly breaks down latency into 4 distinct phases with P50, P95, and P99 percentiles:

1. **Modbus RTT** ($t_{\text{response}} - t_{\text{request}}$): Network round-trip to the Selec PLC.
2. **Edge Processing Lag**: Time taken on the Pi 5 to decode registers and check alarms.
3. **Server Publish Lag**: WebSocket broadcast latency from backend to clients.
4. **DOM Render Lag** ($t_{\text{render}} - t_{\text{publish}}$): High-resolution browser timestamp delta to screen paint.

---

## 🛡️ Industrial Safe Control Architecture

Remote outputs (such as triggering the product pusher actuator or starting the VFD) follow strict fail-safe rules:
* Controlled via `ALLOW_REMOTE_CONTROL=true` toggle in `.env`.
* Cryptographic one-time token authorization with short expiry (10 seconds).
* Interlock verification (checks E-Stop DI `10000` and conveyor running state before pulsing).
* Hardware command verification loop (verifies physical confirmation within 300 ms).
* Complete audit logging in SQLite with millisecond timestamps and client IP tracking.

---

## 🚀 Running 24/7 as a Background Service (Systemd)

To make the dashboard start automatically whenever the Raspberry Pi powers on:

```bash
sudo cp deploy/systemd/selec-iot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable selec-iot.service
sudo systemctl start selec-iot.service
```

Check service status or live logs anytime with:
```bash
sudo systemctl status selec-iot.service
sudo journalctl -u selec-iot.service -f
```

---

## 📂 Project Structure

```text
Selec-PLC-Dashboard/
├── start.sh                      # One-click start script for Linux / Raspberry Pi
├── start.bat                     # One-click start script for Windows
├── .env.example                  # Environment configuration template
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point & WebSocket hubs
│   │   ├── plc/                  # PyModbus 3 client & register decoders
│   │   ├── sensors/              # Load cell, encoder, RTD, energy meter processing
│   │   ├── vibration/            # 1000 Hz decoupled sampling & FFT engine
│   │   ├── latency/              # RTT, processing, and render timing engine
│   │   ├── control/              # 8-step handshake fail-safe control service
│   │   ├── machine/              # Belt slip, pusher state machine & conveyor logic
│   │   └── database/             # SQLite async database models & migrations
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── dist/                     # Pre-compiled React 18 production bundle (zero Pi build needed)
│   └── src/                      # TypeScript + React + Tailwind + Chart.js source code
├── deploy/
│   └── systemd/                  # selec-iot.service definition for auto-start on boot
├── docs/                         # Deployment guides and schematics
└── tools/
    ├── modbus_test.py            # CLI tool for testing PLC communication
    └── latency_benchmark.py      # Automated benchmark runner with CSV export
```

---

## 📄 License
MIT License. Built for industrial prototypes and production Edge IoT deployments.