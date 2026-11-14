# TODO.md — Technical Backlog & Feature Roadmap

> **Purpose**: Track planned improvements, technical debt, and post-v1 enhancements.

---

## Completed Tasks
- [x] Initial FastAPI edge server and Modbus TCP client implementation
- [x] Contiguous Modbus register batch reading and engineering scaling
- [x] ADXL345 I2C accelerometer driver and SciPy FFT engine
- [x] React 19 industrial dark dashboard with 9 complete tabs
- [x] SQLite WAL database buffering and 30-day auto-pruning
- [x] Zero-false-data enforcement in physical mode
- [x] Cross-platform `start.sh` (POSIX) and `start.bat` deployment scripts
- [x] Reconnection rate throttling and asyncio mutex lock in Modbus client

## Post-v1 Backlog
- [ ] Add MQTT publish adapter for optional AWS IoT Core / Azure IoT Hub telemetry replication
- [ ] Add CSV export date-range filter on the Latency and Production tabs
- [ ] Add dark / high-contrast theme toggle for outdoor industrial tablet use

---

*Last updated: 2026-11-14*
