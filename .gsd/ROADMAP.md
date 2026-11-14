---
milestone: v1.0.0-production-ready
version: 1.0.0
updated: 2026-11-14T15:00:00Z
---

# Roadmap

> **Current Milestone:** v1.0.0 - Production Edge Gateway
> **Status:** verified & complete

## Must-Haves (from SPEC)

- [x] PyModbus 3.6 async Modbus TCP client with 3-tier group polling (Fast 200ms, Medium 500ms, Slow 1000ms)
- [x] Edge vibration analysis with 1000 Hz ring buffer, peak/RMS calculation, and FFT spectrum
- [x] Deterministic state management (`COMM_LOST`, `FAULTED`, `RUNNING`, `IDLE`)
- [x] React 19 industrial dark glassmorphism dashboard with 9 complete functional views
- [x] Strict zero-false-data enforcement when physical PLC is disconnected
- [x] Cross-platform one-click launch scripts (`start.sh`, `start.bat`) with auto-venv recovery

---

## Phases

### Phase 1: High-Speed Modbus TCP Edge Ingestion
**Status:** ✅ Complete
**Objective:** Deterministic signal acquisition from Selec MiBRX-6M PLC with register decoding and timestamping.
**Requirements:** REQ-01, REQ-03

**Plans:**
- [x] Plan 1.1: Register mapping parser (`register_map.yaml`) and contiguous block optimization
- [x] Plan 1.2: Asynchronous multi-rhythm polling loops with exponential backoff and connection throttling

---

### Phase 2: Predictive Edge Vibration Analysis & FFT
**Status:** ✅ Complete
**Objective:** ADXL345 I2C accelerometer acquisition and frequency domain decomposition on Raspberry Pi 5.
**Requirements:** REQ-02

**Plans:**
- [x] Plan 2.1: Hardware I2C driver and mock industrial sine wave generator
- [x] Plan 2.2: Ring-buffered SciPy FFT spectrum generation and bearing fault detection

---

### Phase 3: Industrial React 19 Dashboard UI
**Status:** ✅ Complete
**Objective:** Real-time WebSockets telemetry console with 9 dedicated monitoring and control pages.
**Requirements:** REQ-03, REQ-05

**Plans:**
- [x] Plan 3.1: Overview, Live Monitoring, Latency Analytics, and Vibration Visualizer
- [x] Plan 3.2: Production KPI, Energy & Power Metering, Alarms Registry, Safe Control Console, and Settings

---

### Phase 4: Safe Machine Control & Permissive Interlocks
**Status:** ✅ Complete
**Objective:** Strict hardware allowlist control for FC 05 coils and FC 06 registers with operator confirmation.
**Requirements:** REQ-04

**Plans:**
- [x] Plan 4.1: Permissive safety checks (E-Stop, safety guards, VFD fault status)
- [x] Plan 4.2: Operator audit logging and tamper-proof command validation

---

### Phase 5: Hardware Disconnection Failsafe & Deployment Hardening
**Status:** ✅ Complete
**Objective:** Zero false telemetry in physical mode, live PLC configuration, and production start scripts.
**Requirements:** REQ-01, REQ-05

**Plans:**
- [x] Plan 5.1: Suppress all fallback simulation data in physical disconnected mode
- [x] Plan 5.2: POSIX and Windows start script hardening with automated cross-platform venv recreation

---

*Last updated: 2026-11-14*
