# JOURNAL.md — Project Activity & Evolution Log

> **Purpose**: Log major development milestones, design iterations, and release notes.

---

## [2026-11-14] — v1.0.0 Production Release & Hardware Failsafe Hardening

### Summary
- Completely eliminated simulated telemetry leaks when Simulation Mode is OFF.
- Added live hardware detection status badges (`PLC DETECTED` vs `PLC NOT DETECTED`) across all 9 dashboard views.
- Upgraded `start.sh` with pure POSIX standard redirects (`>/dev/null 2>&1`), desktop GUI auto-browser launch, and clean SIGINT (Ctrl+C) handling.
- Enhanced `start.bat` with automated Linux/Windows venv cross-platform sanitization.
- Established canonical GSD project architecture, roadmap, and specification documents.

## [2026-10-12] — Initial Gateway MVP & Prototype Dashboard

### Summary
- Scaffolded FastAPI edge server, PyModbus polling tasks, SQLite WAL schema, and React 19 UI prototype.
- Implemented high-frequency ADXL345 vibration ring-buffer and FFT spectrum analysis.

---

*Last updated: 2026-11-14*
