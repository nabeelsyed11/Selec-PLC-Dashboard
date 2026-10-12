---
updated: 2026-10-12T16:16:00Z
---

# Project State: Selec MiBRX-6M Industrial IoT Monitoring, Latency Measurement and Control Dashboard

## Current Position

**Milestone:** industrial-iot-v1
**Phase:** 10 - Deployment & Commissioning
**Status:** Complete & Verified
**Plan:** All 10 phases executed, tested, and validated.

## Last Action

Completed full project implementation across all 10 phases:
1. Python FastAPI async backend with PyModbus client and connection recovery.
2. Latency monitoring subsystem with microsecond monotonic clock decomposition and statistical percentiles (P50, P95, P99).
3. Decoupled vibration acquisition engine with RMS, Peak, Pk-Pk, and FFT frequency spectrum extraction.
4. Safe, disabled-by-default remote control architecture with strict allowlist and immutable SQLite audit logging.
5. High-fidelity in-process simulation mode with realistic physics, faults, and thermal inertia.
6. React + TypeScript + Vite responsive industrial web dashboard with all 8 operational pages.
7. 15 automated pytest test cases passing cleanly.
8. Complete deployment bundle with systemd service unit, Docker Compose, commissioning checklist, hardware verification checklist, troubleshooting guide, and security hardening guide.

## Active Decisions

| Decision | Choice | Made | Affects |
|---|---|---|---|
| Modbus Library | PyModbus 3.16+ async client | 2026-10-12 | Modbus polling layer |
| Database Engine | SQLite with Write-Ahead Logging (WAL) | 2026-10-12 | Persistence layer |
| Latency Clocks | `time.perf_counter()` for interval RTT + ISO8601 UTC for event logging | 2026-10-12 | Latency measurement accuracy |
| Vibration Decoupling | Independent background acquisition thread/async task with ring buffer | 2026-10-12 | High-speed sampling decoupled from PLC poll |
| Control Safety | Disabled by default + strict register allowlist + 2-step confirmation modal | 2026-10-12 | Machine safety and remote control operations |
| Frontend Stack | React 18/19 + TypeScript + Vite + Modern Industrial CSS Tokens + Lucide Icons | 2026-10-12 | Web dashboard |

## Blockers

None. Application is deployment-ready on Raspberry Pi 5 and testable offline via high-fidelity simulation.
