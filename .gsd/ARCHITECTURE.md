# ARCHITECTURE.md — System Design & Data Flow

> System: Selec MiBRX-6M Industrial IoT Monitoring, Latency Measurement & Control Platform
> Edge Computer: Raspberry Pi 5 (8GB / 4GB, 64-bit OS)
> PLC: Selec MiBRX-6M Micro-PLC with Modbus TCP

---

## 1. System Block Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           INDUSTRIAL FIELD DEVICES                             │
│                                                                                │
│  [Load Cell]  [Motor RTD]  [Belt Sensor]  [Optical Enc]  [Energy Meter RS-485] │
│      │             │            │               │                 │            │
│  [Pusher Solenoid & Limit]  [VFD Analog & Digital IO]                         │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │ Hardware Wiring
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                       SELEC MiBRX-6M PLC (MODBUS SERVER)                       │
│  - Real-time ladder / function block sequencing                                │
│  - Hardware safety interlocks & hardware E-Stop handling                       │
│  - Modbus TCP Server listening on TCP Port 502 (or simulated 5020)             │
│  - Modbus Holding Registers (40001+), Inputs (30001+), Coils (00001+)          │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │ Ethernet (Industrial Subnet / Private LAN)
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                         RASPBERRY PI 5 EDGE GATEWAY                            │
│                                                                                │
│   ┌────────────────────────────────┐    ┌───────────────────────────────────┐  │
│   │     MODBUS POLLER SERVICE      │    │    VIBRATION ACQUISITION ENGINE   │  │
│   │ - Async PyModbus Client        │    │ - Direct I2C/SPI/ADC/Mock Driver  │  │
│   │ - Grouped register reads       │    │ - 1000 - 3200 Hz decoupled task   │  │
│   │ - Adaptive backoff / reconnect │    │ - Ring buffer & FFT extraction    │  │
│   │ - Timestamping (t_req, t_resp) │    │ - RMS, Peak, Pk-to-Pk, dominant Hz│  │
│   └───────────────┬────────────────┘    └─────────────────┬─────────────────┘  │
│                   │ Raw Modbus Registers                  │ Vibration Packets  │
│                   ▼                                       │                    │
│   ┌────────────────────────────────┐                      │                    │
│   │   DECODER & SENSOR PROCESSOR   │                      │                    │
│   │ - Endianness & IEEE-754 decode │                      │                    │
│   │ - Tare & Calibration scaling   │                      │                    │
│   │ - Encoder speed & rollover     │                      │                    │
│   │ - Belt slip detection logic    │                      │                    │
│   │ - OEE count & rate calculation │                      │                    │
│   └───────────────┬────────────────┘                      │                    │
│                   │ Processed Signals                     │                    │
│                   ▼                                       ▼                    │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                   LATENCY MONITOR & BENCHMARK ENGINE                    │  │
│   │ - t_sample, t_plc, t_request, t_response, t_ingest, t_publish           │  │
│   │ - Microsecond monotonic delta calculation                               │  │
│   │ - Rolling percentile window (P50, P95, P99, min, max, jitter)           │  │
│   │ - Data staleness marking & packet error rate                            │  │
│   └────────────────────────────────┬────────────────────────────────────────┘  │
│                                    │                                           │
│         ┌──────────────────────────┴──────────────────────────┐                │
│         ▼                                                     ▼                │
│   ┌───────────────────────────┐                         ┌───────────────────┐  │
│   │  MACHINE STATE & ALARMS   │                         │ SAFE CONTROL SVC  │  │
│   │ - Operating mode engine   │                         │ - Strict allowlist│  │
│   │ - High-temp & slip alarms │                         │ - Permissive check│  │
│   │ - VFD fault detection     │                         │ - Two-man confirm │  │
│   │ - Ack & severity tracking │                         │ - Readback check  │  │
│   └─────────────┬─────────────┘                         │ - Audit log store │  │
│                 │                                       └─────────┬─────────┘  │
│                 ▼                                                 ▼            │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                  SQLITE WAL DATABASE (PERSISTENCE LAYER)                │  │
│   │ - Signal snapshots & historical logs                                    │  │
│   │ - Latency observation records                                           │  │
│   │ - Active and acknowledged alarms                                        │  │
│   │ - Control audit log & operator history                                  │  │
│   │ - Production totals (shift & hourly rollups)                            │  │
│   └────────────────────────────────┬────────────────────────────────────────┘  │
│                                    │                                           │
│                                    ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                 FASTAPI ASYNC BACKEND & WEBSOCKET HUB                   │  │
│   │ - REST endpoints: /api/signals, /api/latency, /api/alarms, /api/control │  │
│   │ - High-throughput WebSocket: /ws (streaming broadcasts with backpressure)│  │
│   │ - JWT / Role-based Authentication (Operator vs Admin)                   │  │
│   └────────────────────────────────┬────────────────────────────────────────┘  │
└────────────────────────────────────┼───────────────────────────────────────────┘
                                     │ WebSockets & REST (JSON)
                                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                    RESPONSIVE WEB CLIENT (REACT + TS + VITE)                   │
│                                                                                │
│  [Overview] [Live Monitor] [Latency Analytics] [Vibration FFT] [Production OEE]│
│  [Energy Monitor] [Alarms & Events] [Safe Control Panel with Interlocks]       │
│  - Browser render timestamping (t_render)                                      │
│  - Clear indicators: VALID, STALE, DISCONNECTED, SIMULATED                     │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Timing and Latency Decomposition Chain

```
Sensor Sample          Modbus Request         Modbus Response       Backend Ingest        WebSocket Publish       Browser Render
  (Hardware)             (Pi Socket)            (Pi Socket)           (Validated)            (Broadcast)             (DOM Paint)
      │                      │                      │                      │                      │                       │
   t_sample ─────────────► t_req ───────────────► t_resp ──────────────► t_ingest ──────────────► t_pub ────────────────► t_render
      │                      │                      │                      │                      │                       │
      │                      └────── RTT_modbus ────┘                      │                      │                       │
      │                                 (M2 - M1)                          │                      │                       │
      │                                             └── Ingest Overhead ───┘                      │                       │
      │                                                 (t_ingest - t_resp)                       │                       │
      │                                                                    └── Publish Delay ─────┘                       │
      │                                                                         (t_pub - t_ingest)                        │
      │                                                                                           └── Transit + Render ───┘
      │                                                                                                (t_render - t_pub)
      └──────────────────────────── Total Sensor-to-Display Latency ──────────────────────────────────────────────────────┘
                                          (t_render - t_sample)
```

---

## 3. Database Schema Design (SQLite WAL)

- **`signals_snapshot`**: Holds the current state of every configured signal, its engineering value, quality flag (`VALID`, `STALE`, `DISCONNECTED`, `SIMULATED`), and latest timestamps.
- **`measurements_history`**: Periodic time-series samples of signal values for trend charts and historical reporting.
- **`latency_records`**: Detailed timestamp metrics per signal group for percentile calculation and benchmarking.
- **`alarms`**: Table of active and cleared alarms, timestamp triggered, timestamp acknowledged, severity (`INFO`, `WARNING`, `CRITICAL`), and message.
- **`control_audit_log`**: Every control command, target register, payload value, issuing operator, IP address, permissive check result, readback status, and mechanical feedback state.
- **`production_history`**: Hourly and shift production snapshots to prevent data loss across restarts.

---

## 4. Module Directory Layout

```
Selec PLC Dashboard/
├── .gsd/                     # GSD specifications, roadmap, state, architecture
├── backend/                  # Python backend application
│   ├── app/
│   │   ├── api/              # REST routes and WebSocket endpoint
│   │   ├── core/             # Pydantic settings, logging, security
│   │   ├── database/         # SQLite schema, async session, repository
│   │   ├── plc/              # PyModbus client, decoder, register map, diagnostics
│   │   ├── sensors/          # Signal calculations, calibration, rollover, slip
│   │   ├── vibration/        # Independent vibration engine, FFT, mock/I2C
│   │   ├── latency/          # Timestamp tracking, percentile calculator, benchmark
│   │   ├── machine/          # Machine state engine, alarms manager
│   │   ├── control/          # Safe control service, allowlist, 8-step handshake
│   │   ├── simulation/       # Realistic mock PLC & data generator
│   │   └── main.py           # FastAPI entry point
│   ├── requirements.txt      # Pinned Python dependencies
│   └── tests/                # Automated pytest suite
├── frontend/                 # React + TypeScript + Vite web dashboard
│   ├── src/
│   │   ├── components/       # Reusable UI widgets (cards, gauges, charts, modals)
│   │   ├── pages/            # 8 operational dashboard pages
│   │   ├── services/         # WebSocket client, API client
│   │   ├── types/            # TypeScript interfaces for signals, latency, alarms
│   │   └── App.tsx           # Router and main layout
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── config/
│   └── register_map.yaml     # Industrial register mapping & allowlist
├── tools/
│   ├── modbus_test.py        # Safe register tester & scanner
│   └── latency_benchmark.py  # Latency benchmark runner & CSV exporter
├── deploy/
│   ├── systemd/              # Linux service units
│   └── docker-compose.yml    # Containerized deployment option
└── docs/                     # Commissioning, hardware checklist, troubleshooting
```

---

*Last updated: 2026-11-14*
