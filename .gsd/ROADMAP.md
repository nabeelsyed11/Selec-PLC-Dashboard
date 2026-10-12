---
milestone: industrial-iot-v1
version: 1.0.0
updated: 2026-10-12T16:15:00Z
---

# Roadmap: Selec MiBRX-6M Industrial IoT Monitoring, Latency Measurement and Control Dashboard

> **Current Phase:** Phase 10 - Completed & Verified
> **Status:** ✅ Complete

## Must-Haves (from SPEC)

- [x] SPEC.md finalized and planning lock released.
- [x] Modular Python backend with PyModbus 3+ async engine and connection recovery.
- [x] Comprehensive latency decomposition engine (t_sample, t_plc, t_request, t_response, t_ingest, t_publish, t_render).
- [x] Independent high-frequency vibration acquisition (Mock, I2C/SPI/ADC) with RMS, Peak, Pk-Pk, and FFT spectrum.
- [x] Safe, disabled-by-default control architecture with allowlist, interlocks, confirmation, and audit logs.
- [x] High-fidelity PLC simulator with fault injection, jitter, and drift for realistic offline testing.
- [x] Real-time responsive web dashboard (React, TypeScript, Vite) with 8 dedicated industrial operational views.
- [x] Automated test suite with empirical verification (15/15 passing).
- [x] Deployment bundle (systemd services, Docker Compose, commissioning checklist).

---

## Phases

### Phase 1: Architecture, Foundation & Workspace Inspection
**Status:** ✅ Complete
**Objective:** Finalize SPEC, ROADMAP, STATE, ARCHITECTURE, and inventory hardware requirements.
**Deliverables:**
- `.gsd/SPEC.md`
- `.gsd/ROADMAP.md`
- `.gsd/STATE.md`
- `.gsd/ARCHITECTURE.md`
- `docs/HARDWARE_CHECKLIST.md`

---

### Phase 2: Project Structure, Configuration System & Simulated PLC
**Status:** ✅ Complete
**Objective:** Build clean modular directory tree, Pydantic-based configuration, `config/register_map.yaml`, and high-fidelity PLC simulation engine.
**Deliverables:**
- Directory structure (`backend/`, `frontend/`, `config/`, `deploy/`, `tools/`, `tests/`)
- `config/register_map.yaml` with documented MiBRX-6M hypotheses
- `backend/app/simulation/mock_plc.py` (realistic industrial signal generator with noise, drift, and faults)

---

### Phase 3: Modbus TCP Engine, Register Decoding & Network Diagnostics
**Status:** ✅ Complete
**Objective:** Implement async Modbus TCP client, robust register grouping, endianness decoding, reconnect with exponential backoff, and communication statistics.
**Deliverables:**
- `backend/app/plc/modbus_client.py`
- `backend/app/plc/decoder.py` (INT16, UINT16, INT32, UINT32, FLOAT32, Big/Little/WordSwap)
- `backend/app/plc/register_map.py`
- `backend/app/plc/diagnostics.py` (Packet loss, timeouts, jitter, stale flag)
- `tools/modbus_test.py` (CLI discovery and verification tool)

---

### Phase 4: Database Ingestion, Historical Storage & Latency Subsystem
**Status:** ✅ Complete
**Objective:** SQLite WAL storage schema, batching for high throughput, retention pruning, and comprehensive timestamp-based latency decomposition with percentiles (P50, P95, P99).
**Deliverables:**
- `backend/app/database/models.py` & `session.py`
- `backend/app/latency/monitor.py`
- `backend/app/latency/benchmark.py` & `tools/latency_benchmark.py` (Benchmark mode with CSV export)
- `backend/app/sensors/processing.py` (Load cell calibration, encoder rollover, slip logic, OEE counters)

---

### Phase 5: Decoupled Vibration Acquisition Engine
**Status:** ✅ Complete
**Objective:** Hardware-abstracted vibration sampling running on independent thread/task; compute RMS, Peak, Peak-to-Peak, and FFT frequency spectrum.
**Deliverables:**
- `backend/app/vibration/sensor.py` (Configurable Mock, I2C, SPI, ADC adapters)
- `backend/app/vibration/analysis.py` (Time-domain metrics and FFT frequency extraction)

---

### Phase 6: Backend APIs & Real-time WebSocket Streaming
**Status:** ✅ Complete
**Objective:** FastAPI REST endpoints, WebSocket streaming channel with client ping-pong and message throttling, machine state manager, and alarm manager.
**Deliverables:**
- `backend/app/api/` (REST routes for signals, latency, alarms, control, vibration, system, production)
- `backend/app/api/websocket.py` (High-efficiency JSON broadcast)
- `backend/app/machine/state.py` (Machine mode, OEE calculations)
- `backend/app/machine/alarms.py` (Alarm engine with severity and acknowledgement)

---

### Phase 7: Responsive Real-time Industrial Web Dashboard
**Status:** ✅ Complete
**Objective:** React + TypeScript + Vite frontend with modern dark industrial UI tokens, responsive layouts, live charts, and 8 dedicated views.
**Deliverables:**
- Overview page (`frontend/src/pages/OverviewPage.tsx`)
- Live Monitoring page (`frontend/src/pages/LiveMonitoringPage.tsx`)
- Latency Analytics & Benchmark page (`frontend/src/pages/LatencyAnalyticsPage.tsx`)
- Vibration Waveform & FFT page (`frontend/src/pages/VibrationPage.tsx`)
- Production Analytics page (`frontend/src/pages/ProductionPage.tsx`)
- Energy Monitoring page (`frontend/src/pages/EnergyPage.tsx`)
- Alarms & Events page (`frontend/src/pages/AlarmsPage.tsx`)
- Safe Control Panel (`frontend/src/pages/ControlPanelPage.tsx`)

---

### Phase 8: Safe PLC Control Request Workflow
**Status:** ✅ Complete
**Objective:** Disabled-by-default remote control, strict allowlist validation, two-man confirmation modal, readback vs physical feedback verification, and audit logging.
**Deliverables:**
- `backend/app/control/service.py`
- Safe Control API endpoints and security guards
- Safe Control UI with interlock feedback and audit trail

---

### Phase 9: Automated Testing & Validation
**Status:** ✅ Complete
**Objective:** Run unit and integration tests across decoders, latency percentiles, rollover, alarms, and control allowlists. Prove operation with test outputs.
**Deliverables:**
- 15/15 passing tests in `backend/tests/`
- Full empirical verification output

---

### Phase 10: Raspberry Pi Deployment & Commissioning Package
**Status:** ✅ Complete
**Objective:** Generate systemd unit files, Docker Compose, installation scripts, physical commissioning checklist, security hardening guide, and troubleshooting documentation.
**Deliverables:**
- `deploy/systemd/selec-iot.service`
- `docker-compose.yml` and `Dockerfile`
- `docs/COMMISSIONING_CHECKLIST.md`
- `docs/HARDWARE_CHECKLIST.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/TROUBLESHOOTING.md`
- `docs/SECURITY_GUIDE.md`
