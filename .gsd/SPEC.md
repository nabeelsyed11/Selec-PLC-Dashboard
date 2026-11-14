# SPEC.md — Project Specification

> **Status**: `FINALIZED`
>
> ⚠️ **Planning Lock**: Requirements and specification are finalized and verified.

## Vision
The Selec MiBRX-6M Industrial IoT Edge Gateway is an open, high-reliability edge telemetry platform designed for Raspberry Pi 5. It continuously queries physical Selec PLCs over Modbus TCP, performs edge vibration FFT analysis via I2C accelerometers, enforces fail-safe physical machine interlocks, and streams real-time industrial SCADA telemetry to browser dashboards at 10 Hz over WebSockets.

## Goals
1. **Deterministic Modbus Acquisition** — Read discrete inputs and numerical holding registers in prioritized groups (200ms, 500ms, 1000ms) with sub-millisecond precision.
2. **Predictive Vibration Analysis** — Ingest 3-axis acceleration data at 1000 Hz from an ADXL345 accelerometer and compute peak, RMS, crest factor, and FFT spectrum on the edge.
3. **Fail-Safe Disconnection Handling** — Guarantee that when physical mode is active and the PLC is offline, no false or simulated telemetry is ever shown; all signals are held strictly at 0.0 with `COMM_LOST` indicators.
4. **Hardware-Safe Remote Actuation** — Restrict remote output writes to a strict allowlist of FC 05 coils and FC 06 registers, locked by mechanical permissive interlocks.
5. **Zero-Configuration Raspberry Pi Deployment** — Provide automated one-click `start.sh` and `start.bat` scripts with cross-platform venv recovery and pre-compiled frontend assets.

## Non-Goals (Out of Scope)
- Direct cloud-only ingestion without edge buffering.
- Proprietary closed-source SCADA software licensing.
- Arbitrary unvalidated Modbus register writes outside configured safety bounds.

## Constraints
- **Hardware Target**: Raspberry Pi 5 (ARM64) running Raspberry Pi OS (Debian 12 Bookworm), and Windows 10/11 for local development.
- **Field PLC Protocol**: Modbus TCP over standard Ethernet (Port 502, Unit ID 1).
- **Storage Protection**: Raspberry Pi SD-card wear mitigation using SQLite WAL mode and 1.0s in-memory buffering.

## Success Criteria
- [x] End-to-end latency below 50 ms for fast group telemetry.
- [x] 100% test pass rate across PLC decoder, vibration engine, and sensor processing.
- [x] Automatic fallback suppression: simulation values never appear when physical mode is selected.
- [x] One-click startup scripts (`start.sh` and `start.bat`) functional without manual package compilation.
- [x] Responsive React 19 operator console accessible on local network without Node.js on edge gateway.

## Technical Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| REQ-01: Modbus TCP Client | Must-have | PyModbus 3.6 async client with 3-tier polling engine |
| REQ-02: Vibration FFT Engine | Must-have | SciPy FFT with ADXL345 I2C driver and mock fallbacks |
| REQ-03: Real-Time WebSockets | Must-have | 10 Hz periodic telemetry push to connected browsers |
| REQ-04: Allowlist Safe Control | Must-have | Permissive interlocks (E-stop, guards, VFD) with operator audit |
| REQ-05: Real-Time Configuration | Must-have | Live IP, port, and simulation toggle without gateway restart |

---

*Last updated: 2026-11-14*
