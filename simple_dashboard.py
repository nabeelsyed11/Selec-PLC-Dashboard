#!/usr/bin/env python3
"""
Selec MiBRX-6M PLC - Complete Industrial SCADA Live Dashboard
Single-file, rock-solid, zero-configuration architecture.
Reads and monitors all requested Selec PLC registers:
  * First Cycle:  PLC MX2 (bool)   -> Modbus Coil 514 (FC 01)
  * Second Cycle: PLC MX3 (bool)   -> Modbus Coil 515 (FC 01)
  * Third Cycle:  PLC MX4 (bool)   -> Modbus Coil 516 (FC 01)
  * Fourth Cycle: PLC MX5 (bool)   -> Modbus Coil 517 (FC 01)
  * Scaled Out:   PLC QW0 (real)   -> Modbus 30768 / 767 in Hz (float32, FC 04/03)
  * Input IW0:    PLC IW0 (int16)  -> Modbus 40768 / 767 raw integer (FC 03/04)
  * Mains Volt:   PLC TD3 (real)   -> Modbus 41542 / 1541 in V (float32, FC 03)
  * Load Current: PLC TD4 (real)   -> Modbus 41544 / 1543 in A (float32, FC 03)
  * Power Factor: PLC TD4/5 (real) -> Modbus 41546 / 1545 in PF (float32, FC 03)
"""
import asyncio
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import struct
import sys
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from pymodbus.client import AsyncModbusTcpClient

# Helper: Version-agnostic PyModbus caller (supports device_id, slave, unit)
def call_modbus(method, *args, unit_id: int = 1, **kwargs):
    import inspect
    try:
        params = inspect.signature(method).parameters
        if "device_id" in params:
            kwargs["device_id"] = unit_id
        elif "slave" in params:
            kwargs["slave"] = unit_id
        elif "unit" in params:
            kwargs["unit"] = unit_id
        else:
            kwargs["device_id"] = unit_id
    except Exception:
        kwargs["device_id"] = unit_id
    return method(*args, **kwargs)

def decode_float32(r1: int, r2: int, word_swap: bool = False) -> float:
    """Decode IEEE-754 32-bit float from 2 consecutive 16-bit registers (with auto endian check)."""
    try:
        if word_swap:
            r1, r2 = r2, r1
        packed = struct.pack(">HH", r1 & 0xFFFF, r2 & 0xFFFF)
        val = struct.unpack(">f", packed)[0]
        # Auto-detect word swap if out of expected industrial range
        if val != val or abs(val) > 1e6 or (abs(val) < 1e-4 and abs(val) > 0):
            packed_swap = struct.pack(">HH", r2 & 0xFFFF, r1 & 0xFFFF)
            val_swap = struct.unpack(">f", packed_swap)[0]
            if not (val_swap != val_swap) and abs(val_swap) <= 1e6:
                return float(val_swap)
            return 0.0
        return float(val)
    except Exception:
        return 0.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scada_dashboard")

app = FastAPI(title="Selec PLC SCADA Dashboard")

# Read environment configuration or fallback to defaults
PLC_HOST = os.getenv("PLC_HOST", "192.168.1.50")
PLC_PORT = int(os.getenv("PLC_PORT", 502))
PLC_UNIT_ID = int(os.getenv("PLC_UNIT_ID", 1))

# Global shared state
state = {
    "connected": False,
    "plc_host": PLC_HOST,
    "plc_port": PLC_PORT,
    "unit_id": PLC_UNIT_ID,
    "address_detected": "Scanning registers...",
    "rtt_ms": 0.0,
    "last_update": None,
    # SCADA Cycles (MX2..MX5)
    "cycle_1": False,
    "cycle_2": False,
    "cycle_3": False,
    "cycle_4": False,
    # SCADA Telemetry Registers
    "iw0_value": 0,          # PLC IW0 (int16, raw)
    "vfd_out_hz": 0.0,       # PLC QW0 (float32, Hz)
    "voltage_td3": 0.0,      # PLC TD3 (float32, V)
    "current_td4": 0.0,      # PLC TD4 (float32, A)
    "power_factor_td5": 0.0, # PLC TD4/5 (float32, PF)
    # Trend history
    "history": [],
}

active_websockets = set()

async def client_read_hr(client, address, unit_id, count=1):
    return await call_modbus(client.read_holding_registers, address=address, count=count, unit_id=unit_id)

async def client_read_ir(client, address, unit_id, count=1):
    return await call_modbus(client.read_input_registers, address=address, count=count, unit_id=unit_id)

async def modbus_polling_task():
    """Background task to discover and poll all Selec PLC registers continuously."""
    client = None

    # Candidate list for IW0 (Address 40768) - exact list that worked previously
    candidate_list = [
        (client_read_hr, 767, "Holding Reg 767 (Modbus 40768 1-based)", -1),
        (client_read_hr, 768, "Holding Reg 768 (Modbus 40768 0-based)", 0),
        (client_read_ir, 767, "Input Reg 767 (Modbus 30768 1-based)", -1),
        (client_read_ir, 768, "Input Reg 768 (Modbus 30768 0-based)", 0),
        (client_read_hr, 40768, "Holding Reg 40768 (Literal)", 40000),
        (client_read_hr, 40767, "Holding Reg 40767 (Literal 0-based)", 40000),
        (client_read_ir, 40768, "Input Reg 40768 (Literal)", 30000),
    ]

    active_read_fn = None
    active_address = None
    active_offset = 0

    while True:
        try:
            if client is None or not getattr(client, "connected", False):
                logger.info(f"Connecting to Selec PLC at {PLC_HOST}:{PLC_PORT} (Unit: {PLC_UNIT_ID})...")
                client = AsyncModbusTcpClient(PLC_HOST, port=PLC_PORT, timeout=1.5)
                connected = await client.connect()
                if not connected:
                    state["connected"] = False
                    await asyncio.sleep(2.0)
                    continue
                state["connected"] = True
                logger.info(f"✓ CONNECTED to Selec PLC at {PLC_HOST}:{PLC_PORT} successfully!")

            t0 = time.perf_counter()

            # ------------------------------------------------------------------
            # 1. Primary Heartbeat: Read IW0 (PLC Input Address IW0)
            # ------------------------------------------------------------------
            val_found = None
            if active_read_fn is not None and active_address is not None:
                try:
                    resp = await active_read_fn(client, active_address, PLC_UNIT_ID)
                    if not resp.isError() and hasattr(resp, "registers") and resp.registers:
                        val_found = resp.registers[0]
                except Exception:
                    active_read_fn = None
                    active_address = None

            # Discovery scan if not locked onto working address yet
            if val_found is None:
                for fn, addr, desc, offset in candidate_list:
                    try:
                        resp = await fn(client, addr, PLC_UNIT_ID)
                        if not resp.isError() and hasattr(resp, "registers") and resp.registers:
                            val_found = resp.registers[0]
                            active_read_fn = fn
                            active_address = addr
                            active_offset = offset
                            state["address_detected"] = f"{desc}"
                            logger.info(f"✓ Locked onto IW0 at {desc}! Value: {val_found}")
                            break
                    except Exception:
                        continue

            t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if val_found is not None:
                state["connected"] = True
                state["rtt_ms"] = round(t_elapsed_ms, 1)
                raw_int16 = val_found if val_found < 32768 else val_found - 65536
                state["iw0_value"] = raw_int16
                now_str = datetime.now().strftime("%H:%M:%S")
                state["last_update"] = now_str

                # Keep last 50 historical points for live trend chart
                state["history"].append({
                    "time": now_str,
                    "iw0": state["iw0_value"],
                    "vfd": state["vfd_out_hz"],
                })
                if len(state["history"]) > 50:
                    state["history"].pop(0)

            # ------------------------------------------------------------------
            # 2. Read Cycles MX2..MX5 (Coils 514..517 or 513..516)
            # ------------------------------------------------------------------
            try:
                cycle_addr = 514 if active_offset == 0 else 513
                coils = await call_modbus(client.read_coils, address=cycle_addr, count=4, unit_id=PLC_UNIT_ID)
                if not coils.isError() and hasattr(coils, "bits") and len(coils.bits) >= 4:
                    state["cycle_1"] = bool(coils.bits[0])
                    state["cycle_2"] = bool(coils.bits[1])
                    state["cycle_3"] = bool(coils.bits[2])
                    state["cycle_4"] = bool(coils.bits[3])
                else:
                    # Alternative: Discrete Inputs FC 02
                    di = await call_modbus(client.read_discrete_inputs, address=cycle_addr, count=4, unit_id=PLC_UNIT_ID)
                    if not di.isError() and hasattr(di, "bits") and len(di.bits) >= 4:
                        state["cycle_1"] = bool(di.bits[0])
                        state["cycle_2"] = bool(di.bits[1])
                        state["cycle_3"] = bool(di.bits[2])
                        state["cycle_4"] = bool(di.bits[3])
            except Exception:
                pass

            # ------------------------------------------------------------------
            # 3. Read Scaled Out / VFD Out QW0 (Float32 in Hz)
            # ------------------------------------------------------------------
            try:
                qw0_addr = active_address if active_address is not None else (767 if active_offset == -1 else 768)
                qw0_r = await call_modbus(client.read_input_registers, address=qw0_addr, count=2, unit_id=PLC_UNIT_ID)
                if not qw0_r.isError() and hasattr(qw0_r, "registers") and len(qw0_r.registers) >= 2:
                    val = decode_float32(qw0_r.registers[0], qw0_r.registers[1])
                    state["vfd_out_hz"] = round(val, 1)
                else:
                    qw0_hr = await call_modbus(client.read_holding_registers, address=qw0_addr, count=2, unit_id=PLC_UNIT_ID)
                    if not qw0_hr.isError() and hasattr(qw0_hr, "registers") and len(qw0_hr.registers) >= 2:
                        val = decode_float32(qw0_hr.registers[0], qw0_hr.registers[1])
                        state["vfd_out_hz"] = round(val, 1)
            except Exception:
                pass

            # ------------------------------------------------------------------
            # 4. Read Electrical Telemetry: TD3 (Voltage), TD4 (Current), TD4/5 (PF)
            # Starting at address 1541 (1-based) or 1542 (0-based)
            # ------------------------------------------------------------------
            try:
                td_addr = 1541 if active_offset == -1 else 1542
                td_r = await call_modbus(client.read_holding_registers, address=td_addr, count=6, unit_id=PLC_UNIT_ID)
                if not td_r.isError() and hasattr(td_r, "registers") and len(td_r.registers) >= 6:
                    regs = td_r.registers
                    state["voltage_td3"] = round(decode_float32(regs[0], regs[1]), 1)
                    state["current_td4"] = round(decode_float32(regs[2], regs[3]), 2)
                    state["power_factor_td5"] = round(decode_float32(regs[4], regs[5]), 2)
            except Exception:
                pass

            # Broadcast state to connected WebSocket clients
            if active_websockets:
                payload = json.dumps(state)
                dead = set()
                for ws in list(active_websockets):
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        dead.add(ws)
                active_websockets.difference_update(dead)

        except Exception as e:
            logger.warning(f"Modbus poll cycle error: {e}")
            state["connected"] = False
            if client:
                try:
                    client.close()
                except Exception:
                    pass
                client = None
            await asyncio.sleep(2.0)

        await asyncio.sleep(0.2)  # 5 Hz update rate

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(modbus_polling_task())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_websockets.add(ws)
    await ws.send_text(json.dumps(state))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        active_websockets.discard(ws)

@app.get("/api/data")
async def get_data():
    return state

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Selec PLC - SCADA Live Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --border: #1f2937;
      --cyan: #06b6d4;
      --green: #10b981;
      --amber: #f59e0b;
      --blue: #3b82f6;
      --purple: #8b5cf6;
      --red: #ef4444;
      --text: #f9fafb;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      padding: 16px;
      min-height: 100vh;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    header {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    h1 {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.5px;
      color: #fff;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge.online {
      background: rgba(16, 185, 129, 0.15);
      color: var(--green);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge.offline {
      background: rgba(239, 68, 68, 0.15);
      color: var(--red);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 8px currentColor;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
    }
    .section-title {
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-muted);
      margin-bottom: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .cycles-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .cycle-card {
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      transition: all 0.2s ease;
    }
    .cycle-card.active {
      border-color: var(--green);
      background: rgba(16, 185, 129, 0.08);
      box-shadow: 0 0 16px rgba(16, 185, 129, 0.15);
    }
    .cycle-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--text-muted);
    }
    .cycle-name {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }
    .cycle-meta {
      font-family: monospace;
      font-size: 11px;
      color: var(--text-muted);
    }
    .cycle-pill {
      align-self: flex-start;
      margin-top: 4px;
      font-size: 10px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(255,255,255,0.06);
      color: var(--text-muted);
    }
    .cycle-card.active .cycle-pill {
      background: var(--green);
      color: #000;
    }
    .telemetry-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 14px;
    }
    .telemetry-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .t-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .t-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .t-meta {
      font-family: monospace;
      font-size: 10px;
      color: var(--text-muted);
    }
    .t-value {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 32px;
      font-weight: 800;
      color: #fff;
      line-height: 1.1;
    }
    .t-unit {
      font-size: 15px;
      font-weight: 600;
    }
    .t-sub {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 6px;
    }
    .chart-container {
      position: relative;
      height: 240px;
      width: 100%;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Selec MiBRX-6M SCADA Dashboard</h1>
        <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">
          Modbus TCP Master &bull; <strong>192.168.1.50:502</strong> (Slave ID 1) &bull; <span id="lock-info" style="color: var(--cyan); font-weight: 600;">Scanning...</span>
        </div>
      </div>
      <div id="conn-badge" class="badge offline">
        <span class="dot"></span>
        <span id="conn-text">CONNECTING...</span>
      </div>
    </header>

    <!-- 1. SCADA Process Cycle Sequencer (MX2 - MX5) -->
    <div class="card">
      <div class="section-title">
        <span>Process Cycle Sequencer (MX2 - MX5)</span>
        <span style="font-size: 11px; color: var(--text-muted);">Modbus Coils: 514 - 517</span>
      </div>
      <div class="cycles-grid">
        <div class="cycle-card" id="card-cycle-1">
          <div class="cycle-label">First Cycle</div>
          <div class="cycle-name">Cycle 1</div>
          <div class="cycle-meta">PLC: <strong>MX2</strong> | Modbus: 514</div>
          <div class="cycle-pill" id="pill-cycle-1">STANDBY</div>
        </div>
        <div class="cycle-card" id="card-cycle-2">
          <div class="cycle-label">Second Cycle</div>
          <div class="cycle-name">Cycle 2</div>
          <div class="cycle-meta">PLC: <strong>MX3</strong> | Modbus: 515</div>
          <div class="cycle-pill" id="pill-cycle-2">STANDBY</div>
        </div>
        <div class="cycle-card" id="card-cycle-3">
          <div class="cycle-label">Third Cycle</div>
          <div class="cycle-name">Cycle 3</div>
          <div class="cycle-meta">PLC: <strong>MX4</strong> | Modbus: 516</div>
          <div class="cycle-pill" id="pill-cycle-3">STANDBY</div>
        </div>
        <div class="cycle-card" id="card-cycle-4">
          <div class="cycle-label">Fourth Cycle</div>
          <div class="cycle-name">Cycle 4</div>
          <div class="cycle-meta">PLC: <strong>MX5</strong> | Modbus: 517</div>
          <div class="cycle-pill" id="pill-cycle-4">STANDBY</div>
        </div>
      </div>
    </div>

    <!-- 2. SCADA Telemetry Cards -->
    <div class="telemetry-grid">
      <!-- Scaled Out / VFD Out QW0 -->
      <div class="telemetry-card">
        <div class="t-header">
          <span class="t-label" style="color: var(--cyan);">VFD Out Speed</span>
          <span class="t-meta">QW0 (30768)</span>
        </div>
        <div class="t-value" id="val-vfd">0.0 <span class="t-unit" style="color: var(--cyan);">Hz</span></div>
        <div class="t-sub">Scaled Output (float32)</div>
      </div>

      <!-- Process Input Word IW0 -->
      <div class="telemetry-card">
        <div class="t-header">
          <span class="t-label" style="color: var(--green);">Process Input</span>
          <span class="t-meta">IW0 (40768)</span>
        </div>
        <div class="t-value" id="val-iw0">0 <span class="t-unit" style="color: var(--green);">raw</span></div>
        <div class="t-sub">Input Register (int16)</div>
      </div>

      <!-- Mains Voltage TD3 -->
      <div class="telemetry-card">
        <div class="t-header">
          <span class="t-label" style="color: var(--amber);">Mains Voltage</span>
          <span class="t-meta">TD3 (41542)</span>
        </div>
        <div class="t-value" id="val-voltage">0.0 <span class="t-unit" style="color: var(--amber);">V</span></div>
        <div class="t-sub">Line Potential (float32)</div>
      </div>

      <!-- Load Current TD4 -->
      <div class="telemetry-card">
        <div class="t-header">
          <span class="t-label" style="color: var(--blue);">Load Current</span>
          <span class="t-meta">TD4 (41544)</span>
        </div>
        <div class="t-value" id="val-current">0.00 <span class="t-unit" style="color: var(--blue);">A</span></div>
        <div class="t-sub">Motor Current (float32)</div>
      </div>

      <!-- Power Factor TD4/5 -->
      <div class="telemetry-card">
        <div class="t-header">
          <span class="t-label" style="color: var(--purple);">Power Factor</span>
          <span class="t-meta">TD4/5 (41546)</span>
        </div>
        <div class="t-value" id="val-pf">0.00 <span class="t-unit" style="color: var(--purple);">PF</span></div>
        <div class="t-sub">Power Factor (float32)</div>
      </div>
    </div>

    <!-- 3. Live Historical Trend Chart -->
    <div class="card">
      <div class="section-title">
        <span>Live Telemetry Trend (IW0 & VFD Speed)</span>
        <span id="rtt-text" style="font-family: monospace; font-size: 11px; color: var(--text-muted);">RTT: -- ms</span>
      </div>
      <div class="chart-container">
        <canvas id="trendChart"></canvas>
      </div>
    </div>
  </div>

  <script>
    // Initialize Live Chart
    const ctx = document.getElementById('trendChart').getContext('2d');
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Process Input IW0 (raw)',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderWidth: 2,
            tension: 0.25,
            yAxisID: 'y',
          },
          {
            label: 'VFD Out (Hz)',
            data: [],
            borderColor: '#06b6d4',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0.25,
            yAxisID: 'y1',
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#6b7280', maxTicksLimit: 8 }
          },
          y: {
            position: 'left',
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#10b981' },
            title: { display: true, text: 'IW0 (counts)', color: '#10b981' }
          },
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#06b6d4' },
            title: { display: true, text: 'VFD (Hz)', color: '#06b6d4' }
          }
        },
        plugins: {
          legend: { labels: { color: '#9ca3af' } }
        }
      }
    });

    // WebSocket Client
    let ws = null;
    function connectWs() {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${proto}//${window.location.host}/ws`);

      ws.onopen = () => {
        console.log("WebSocket connected.");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          updateUI(data);
        } catch (e) {
          console.error("Parse error:", e);
        }
      };

      ws.onclose = () => {
        document.getElementById('conn-badge').className = 'badge offline';
        document.getElementById('conn-text').textContent = 'DISCONNECTED';
        setTimeout(connectWs, 2000);
      };
    }

    function updateUI(data) {
      // 1. Connection Badge & Lock Info
      const badge = document.getElementById('conn-badge');
      const text = document.getElementById('conn-text');
      if (data.connected) {
        badge.className = 'badge online';
        text.textContent = 'PLC ONLINE (' + data.rtt_ms + ' ms)';
      } else {
        badge.className = 'badge offline';
        text.textContent = 'PLC OFFLINE';
      }

      if (data.address_detected) {
        document.getElementById('lock-info').textContent = 'Locked on: ' + data.address_detected;
      }

      // 2. Cycles MX2..MX5
      for (let i = 1; i <= 4; i++) {
        const active = Boolean(data['cycle_' + i]);
        const card = document.getElementById('card-cycle-' + i);
        const pill = document.getElementById('pill-cycle-' + i);
        if (active) {
          card.className = 'cycle-card active';
          pill.textContent = 'ACTIVE';
        } else {
          card.className = 'cycle-card';
          pill.textContent = 'STANDBY';
        }
      }

      // 3. Telemetry Values
      document.getElementById('val-vfd').innerHTML = (data.vfd_out_hz || 0).toFixed(1) + ' <span class="t-unit" style="color: var(--cyan);">Hz</span>';
      document.getElementById('val-iw0').innerHTML = (data.iw0_value || 0) + ' <span class="t-unit" style="color: var(--green);">raw</span>';
      document.getElementById('val-voltage').innerHTML = (data.voltage_td3 || 0).toFixed(1) + ' <span class="t-unit" style="color: var(--amber);">V</span>';
      document.getElementById('val-current').innerHTML = (data.current_td4 || 0).toFixed(2) + ' <span class="t-unit" style="color: var(--blue);">A</span>';
      document.getElementById('val-pf').innerHTML = (data.power_factor_td5 || 0).toFixed(2) + ' <span class="t-unit" style="color: var(--purple);">PF</span>';
      document.getElementById('rtt-text').textContent = `RTT: ${data.rtt_ms || 0} ms`;

      // 4. Update Chart
      if (data.history && data.history.length > 0) {
        chart.data.labels = data.history.map(h => h.time);
        chart.data.datasets[0].data = data.history.map(h => h.iw0);
        chart.data.datasets[1].data = data.history.map(h => h.vfd);
        chart.update();
      }
    }

    connectWs();
  </script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Selec PLC SCADA Dashboard on http://0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
