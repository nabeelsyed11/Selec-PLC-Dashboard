---
status: FINALIZED
created: 2026-10-12T00:00:00Z
finalized: 2026-11-14T15:00:00Z
---

# PROJECT.md — Selec MiBRX-6M Industrial IoT Edge Gateway

## Vision
High-reliability edge computing gateway and SCADA visualization dashboard engineered for Raspberry Pi 5. Provides microsecond-level Modbus TCP polling from Selec MiBRX-6M PLCs, real-time vibration spectral FFT analysis via I2C accelerometers, and 10 Hz reactive WebSocket streaming to local browser clients.

---

## Key Hardware & Systems

- **Industrial Controller:** Selec MiBRX-6M PLC (Static IP `192.168.1.50`, Port `502`, Unit `1`)
- **Gateway Platform:** Raspberry Pi 5 (4GB / 8GB) running Raspberry Pi OS (Debian 12 Bookworm)
- **Vibration Sensor:** ADXL345 3-Axis Digital Accelerometer on I2C Bus 1 (Address `0x53`)
- **Backend Stack:** Python 3.10+, FastAPI, PyModbus 3.6, NumPy, SciPy, SQLite WAL, Uvicorn
- **Frontend Stack:** React 19, TypeScript, Lucide Icons, Vite, HTML5 Canvas, WebSockets

---

## Core Operational Modes

| Mode | PLC Telemetry | Vibration Spectrum | Use Case |
|------|---------------|-------------------|----------|
| **Simulation ON** | Synthetic conveyor physics, motor load, and sensor pulses | Generated 35 Hz / 142 Hz bearing fault waveforms | Offline UI demonstration, driver testing, training |
| **Simulation OFF (Detected)** | Live physical Modbus register readings from field PLC | Live I2C accelerometer samples | Normal factory production operation |
| **Simulation OFF (Offline)** | All held at `0.0` with `COMM_LOST` alarm | Flatline `0.000g` with `NO_HARDWARE` badge | Failsafe network fault indication |

---

*Last updated: 2026-11-14*
