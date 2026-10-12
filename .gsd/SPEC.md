# SPEC.md — Project Specification: Industrial IoT Monitoring, Latency Measurement and Control Dashboard

> **Status**: `FINALIZED`
>
> **Project**: Selec MiBRX-6M Industrial IoT Monitoring, Latency Measurement and Control Dashboard
> **Target Devices**: Selec MiBRX-6M PLC (Modbus TCP server), Raspberry Pi 5 (Edge Gateway & Dashboard Host), Directly Connected Vibration Sensor, Real-time Web Browser Client.

---

## 1. Vision & Executive Summary

This project delivers a deployment-ready, carrier-grade Industrial IoT (IIoT) monitoring, latency benchmarking, and machine control system for an industrial prototype based on the **Selec MiBRX-6M PLC** communicating via Modbus TCP to a **Raspberry Pi 5** edge gateway.

The platform provides:
1. **Deterministic, asynchronous Modbus TCP polling** with register grouping, adaptive reconnection, jitter mitigation, and bounded backoff.
2. **True high-resolution latency decomposition** that strictly separates physical measurement age, PLC processing timestamp, Modbus network round-trip, edge ingestion delay, WebSocket publishing time, and browser render latency.
3. **High-frequency vibration acquisition** operating independently on the Raspberry Pi (supporting simulated, I2C/SPI digital MEMS accelerometers, and analog ADC interfaces) computing RMS, Peak, Peak-to-Peak, and FFT spectral frequency bins without starving or blocking the PLC communication loop.
4. **Safe, interlocked remote control architecture** enforcing an explicit writable register allowlist, role-based authorization, two-man / operator confirmation modals, readback vs. physical feedback validation, and immutable audit logging. Controls are disabled by default.
5. **Real-time industrial dashboard** (React + TypeScript + Vite + Tailwind CSS / Modern CSS tokens + Recharts) streaming via WebSockets with dedicated pages for Overview, Live Monitoring, Latency Analytics & Benchmarking, Vibration FFT, Production OEE Analytics, Energy Monitoring, Alarms & Events, and Safe Control.
6. **Dual-mode operation**: Full high-fidelity simulation mode (realistic PLC Modbus server with simulated faults, temperature drift, belt slip, vibration harmonics, network jitter) and Physical Hardware Mode with complete commissioning checklists.

---

## 2. System Architecture & Boundaries

```
[ Field Sensors & Equipment ]
  │- Load Cell (mV/V or 0-10V/4-20mA to PLC analog in)
  │- Motor Thermistor/RTD (PT100 to PLC temp in)
  │- Belt Slip Proximity Switch (PLC digital in)
  │- Rotary Optical Encoder (PLC high-speed counter HSC)
  │- RS-485 Energy Meter (Modbus RTU master on PLC port)
  │- Production Optical Sensor (PLC digital pulse in)
  │- Pusher Actuator Output & Limit Feedback (PLC DO & DI)
  │- VFD Speed Ref & Feedback (PLC AO & AI)
  │- VFD Run/Stop/Fault/Ready (PLC DO & DI)
               │
               ▼
[ Selec MiBRX-6M PLC ] (Modbus TCP Server / Slave, port 502)
               │
               │ Ethernet (Industrial LAN / Private Subnet)
               ▼
[ Raspberry Pi 5 Edge Gateway ]
  ├── [ Directly Connected Vibration Sensor ] (I2C / SPI / ADC on Pi GPIO)
  │       │
  │       ▼ High-Frequency Vibration Engine (RMS, Peak, Peak-to-Peak, FFT)
  │
  ├── Modbus TCP Poller Engine (Grouped reads, PyModbus async)
  ├── Latency Monitoring Subsystem (t_sample, t_plc, t_request, t_response, t_ingest, t_publish)
  ├── Sensor Processing & Calibration (Tare, Roll-over, Slip detection, Unit conversions)
  ├── Safe Control Service (Allowlist check, 8-step handshake, Audit logger)
  ├── SQLite WAL / Time-Series Storage (Buffered bulk inserts, Retention pruner)
  ├── FastAPI Asynchronous Backend & WebSocket Hub
  └── Real-time Web Dashboard (React + TypeScript + Vite)
```

---

## 3. Detailed Signal Specifications & PLC Map Hypotheses

| Signal Name | Subsystem | Raw Range / Unit | Engineering Range / Unit | Modbus Register Type & Code | Permitted Operations | Calibration / Parameters |
|---|---|---|---|---|---|---|
| Load Cell | Force / Weight | 0 - 4000 counts | 0.0 - 500.0 kg | Holding Reg (FC 03), 16-bit UINT | Read-Only | Zero Tare, Cal Factor (kg/count) |
| Motor Temperature | Thermal | 0 - 1500 (0.1°C) | 0.0 - 150.0 °C | Holding Reg (FC 03), 16-bit INT | Read-Only | Warning: 75°C, Critical: 90°C |
| Belt Slip Sensor | Motion Safety | 0 or 1 | Normal / Slipping | Discrete Input (FC 02) or Coil (FC 01) | Read-Only | Debounce: 50ms; Slip timeout: 500ms |
| Belt Encoder Count | Speed / Position | 0 - 4294967295 | RPM / m/min | Holding Reg (FC 03), 32-bit UINT (2 regs) | Read-Only | Pulses/rev: 1024, Roller circ: 0.314m, Rollover aware |
| Energy Meter V, I, P, PF, kWh | Power & Energy | 32-bit IEEE float | V, A, kW, PF, kWh | Holding Reg (FC 03), 2 regs each | Read-Only | Instantaneous vs Cumulative kWh |
| Production Counter | OEE / Output | 0 - 4294967295 | Parts, Parts/min | Holding Reg (FC 03), 32-bit UINT | Read-Only | Shift reset handling, non-destructive persistence |
| Pusher Actuator Command | Actuation | 0 or 1 | Off / Extend | Coil (FC 01 / FC 05) | Allowlisted Write (Protected) | Requires Interlock bit + Auto mode check |
| Pusher Limit Feedback | Actuation | 0 or 1 | Retracted / Extended | Discrete Input (FC 02) | Read-Only | Mismatch alarm timeout: 1.5s |
| VFD Run Command | Drive Control | 0 or 1 | Stop / Run | Coil (FC 01 / FC 05) | Allowlisted Write (Protected) | Requires Safety Guard closed & No Fault |
| VFD Speed Reference | Drive Control | 0 - 1000 (0.1 Hz) | 0.0 - 100.0 % (0-50 Hz) | Holding Reg (FC 03 / FC 06) | Allowlisted Write (Protected) | Min: 5 Hz, Max: 50 Hz clamp |
| VFD Status & Fault | Drive Control | Bitmask / Coils | Ready, Running, Tripped | Discrete Inputs (FC 02) | Read-Only | VFD Trip alarm with error code |
| Vibration Sensor (Direct) | Condition Monitor | Acceleration (g) | 0 - 16g, RMS, Pk, FFT | Direct Pi 5 (I2C/SPI/ADC/Mock) | Local Pi Acquisition | Sample Rate: 1000 - 3200 Hz; 512-pt FFT |

---

## 4. Latency Decomposition Model (Strict Mathematical Formulation)

Timestamps captured:
- $t_{sample}$: Hardware sample timestamp (extracted from PLC sequence clock if programmed, else marked `null` with explicit documentation).
- $t_{plc}$: Internal PLC processing time if available in Modbus registers.
- $t_{request}$: Monotonic timestamp $M_1$ and UTC wall-clock $W_1$ captured on Raspberry Pi immediately prior to socket transmit of Modbus ADU.
- $t_{response}$: Monotonic timestamp $M_2$ and UTC wall-clock $W_2$ captured on Raspberry Pi upon receiving full Modbus ADU response frame.
- $t_{ingest}$: Timestamp when validation, decode, scaling, and state update completes.
- $t_{publish}$: Timestamp when message is serialized and sent to WebSocket broadcast buffer.
- $t_{render}$: Browser monotonic timestamp upon requestAnimationFrame render of the updated signal.

### Defined Latency Metrics:
1. **Modbus Round-Trip Time ($RTT_{modbus}$)**: $M_2 - M_1$ (microsecond precision via monotonic clock).
2. **Edge Ingestion Overhead ($\Delta t_{ingest}$)**: $t_{ingest} - M_2$.
3. **Edge Publishing Overhead ($\Delta t_{publish}$)**: $t_{publish} - t_{ingest}$.
4. **WebSocket Transit & Render Lag ($\Delta t_{render}$)**: $t_{render} - t_{publish}$ (measured with round-trip ping time offset compensation).
5. **Data Freshness / Data Age**: $t_{now} - W_2$ (or $t_{now} - t_{sample}$ if $t_{sample}$ is valid).
6. **Sampling Interval Jitter**: $|(W_{2,k} - W_{2,k-1}) - \Delta t_{target\_poll}|$.

---

## 5. Safe Control Framework

1. **Remote Control Disabled By Default**: Environment setting `ALLOW_REMOTE_CONTROL=false`. If false, all write endpoints immediately return HTTP 403 Forbidden.
2. **Explicit Allowlist**: Only registers explicitly declared in `config/register_map.yaml` under `writable_allowlist` can ever be targeted. Attempting to write any other address raises a security violation and is logged in the audit trail.
3. **8-Step Control Handshake**:
   - Step 1: User authenticates and possesses `CONTROL_OPERATOR` or `ADMIN` role.
   - Step 2: System verifies PLC link is healthy (heartbeat valid, error rate < 5%, data age < 2s).
   - Step 3: Permissive interlocks checked (E-Stop healthy, Guard Switch Closed, VFD No-Fault).
   - Step 4: Operator confirms intent via UI two-step confirmation modal with command token.
   - Step 5: Modbus write issued to allowlisted coil/register.
   - Step 6: Modbus write response status verified (FC 05/06/15/16 ACK).
   - Step 7: Immediate readback of target coil/register verifies value took effect in PLC memory.
   - Step 8: Physical feedback timer initiated (e.g. pusher extended sensor) to confirm mechanical movement, logging alarm if feedback fails within timeout.
   - Step 9: Write event recorded in immutable audit log table with operator ID, IP, timestamp, target, command value, and outcome.

---

## 6. Non-Goals & Safety Boundaries

- **Emergency Stop & Functional Safety**: The web dashboard and Raspberry Pi are NOT safety-rated controllers. SIL / PL-rated Emergency Stops, safety light curtains, and mechanical guards MUST be wired directly into hardware safety relays or safety-rated inputs on the PLC. The Pi CANNOT override or substitute for functional safety.
- **Closed-Loop Motion Control**: High-speed real-time closed-loop motion control (e.g., servo position loop) runs deterministically on the PLC, not across the Modbus TCP / HTTP layer.
- **Direct Internet Exposure**: The Pi backend must NOT be exposed directly to the public internet without a secure VPN (WireGuard/Tailscale) or reverse proxy with TLS and firewall isolation.

---

## 7. Deliverables Checklist

- [x] Full source code for Backend (FastAPI, PyModbus, SQLite WAL, NumPy FFT).
- [x] Full source code for Frontend (React, TypeScript, Vite, Tailwind CSS / Modern CSS, Lucide icons, Recharts).
- [x] Realistic PLC & Sensor Simulator with simulated faults, temperature alarms, belt slip, and network jitter.
- [x] Safe Modbus CLI testing utility (`tools/modbus_test.py`).
- [x] Latency benchmarking CLI and CSV exporter (`tools/latency_benchmark.py`).
- [x] Configurable register mapping (`config/register_map.yaml`).
- [x] Systemd service units (`deploy/systemd/`).
- [x] Docker Compose deployment configuration (`docker-compose.yml`).
- [x] Automated pytest suite covering decoders, latency percentiles, rollover, alarms, and safe control.
- [x] Complete documentation: Architecture, Commissioning checklist, Hardware checklist, Troubleshooting guide, Security guide.

---

*Last updated: 2026-10-12 | Antigravity AI*
