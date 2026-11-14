# DECISIONS.md — Architecture Decision Records

> **Purpose**: Log significant technical decisions and their rationale.

---

## Decisions

### [DECISION-001] SQLite WAL Mode with In-Memory Buffer for Edge Storage
**Date**: 2026-10-12
**Status**: Accepted

#### Context
Raspberry Pi 5 boots from micro-SD or NVMe storage. High-frequency telemetry (10-20 Hz updates) will exhaust SD-card write endurance within months if written directly per measurement.

#### Decision
Implement a decoupled in-memory `DatabaseBuffer` that aggregates observations and executes bulk commits once every 1.0 second using SQLite WAL (Write-Ahead Logging) and `PRAGMA synchronous = NORMAL`.

#### Consequences
- Zero SD-card burnout risk.
- High concurrent read throughput for dashboard analytics without locking writes.
- Up to 1.0 second of unsaved telemetry loss in the event of an abrupt ungraceful power pull.

---

### [DECISION-002] Zero-False-Data Enforcement in Physical Mode
**Date**: 2026-11-14
**Status**: Accepted

#### Context
When Simulation Mode was turned OFF, an offline or disconnected PLC was previously triggering a fallback to mock values, confusing operators into believing fake data was real measured field values.

#### Decision
Completely decouple simulation from physical mode:
- When Simulation is OFF and PLC is disconnected, immediately set `connected = False`, mark all signals with `quality: "DISCONNECTED"`, hold numerical values at `0.0`, and raise a critical `PLC_COMM_LOST` alarm.
- Never output synthetic sine waves on the vibration channel unless Simulation Mode is explicitly enabled.

#### Consequences
- 100% telemetry integrity.
- Immediate visual detection of disconnected Ethernet cables or network faults.

---

### [DECISION-003] Modbus Reconnection Rate Throttling and Lock
**Date**: 2026-11-14
**Status**: Accepted

#### Context
When the field PLC was offline, three concurrent polling tasks (`fast_group`, `medium_group`, `slow_group`) simultaneously created new Modbus TCP clients and attempted network connections every 100ms, flooding the OS network stack.

#### Decision
Introduce an `asyncio.Lock` and a 3.0-second cooldown timer on all reconnection attempts so only one connection attempt can occur at a time.

#### Consequences
- Clean, stable network behavior with zero CPU thrashing when hardware is disconnected.

---

### [DECISION-004] Pre-compiled Production Bundle Checked into Repository
**Date**: 2026-11-14
**Status**: Accepted

#### Context
Compiling React with TypeScript on a Raspberry Pi requires `Node.js`, `npm`, and significant RAM/CPU compilation overhead.

#### Decision
Compile the Vite/React application into `frontend/dist/` on development machines and serve the pre-built static distribution directly through FastAPI on the Raspberry Pi.

#### Consequences
- Raspberry Pi only needs Python 3.
- Fast startup (< 2 seconds) with no Node.js footprint.

---

*Last updated: 2026-11-14*
