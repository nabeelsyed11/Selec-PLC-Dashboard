#!/usr/bin/env python3
"""
Simple Selec MiBRX-6M PLC Dashboard
Dedicated single-purpose dashboard for reading Input Register IW0 (Address 40768)
in Integer format from 192.168.1.50:502.
"""
import asyncio
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from pymodbus.client import AsyncModbusTcpClient

# Version-agnostic PyModbus caller (supports device_id, slave, unit)
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simple_dashboard")

app = FastAPI(title="Selec PLC IW0 Simple Dashboard")

PLC_HOST = os.getenv("PLC_HOST", "192.168.1.50")
PLC_PORT = int(os.getenv("PLC_PORT", 502))
PLC_UNIT_ID = int(os.getenv("PLC_UNIT_ID", 1))

# Global shared state
state = {
    "connected": False,
    "plc_host": PLC_HOST,
    "plc_port": PLC_PORT,
    "unit_id": PLC_UNIT_ID,
    "address_detected": None,
    "function_code": None,
    "iw0_value": 0,
    "rtt_ms": 0.0,
    "discrete_inputs": [0] * 8,
    "last_update": None,
    "history": [],  # List of {time, value}
}

active_websockets = set()


async def modbus_polling_task():
    """Background task to discover and poll IW0 at address 40768."""
    client = None
    # Candidates for 40768:
    # In Modbus standard: 40768 is 1-based holding register 768 (protocol address 767)
    # 0-based holding register 768
    # Input register (FC 04) 767 / 768
    # Absolute address 40768 / 40767
    candidate_list = [
        (client_read_hr, 767, "Holding Reg 767 (Modbus 40768 1-based)"),
        (client_read_hr, 768, "Holding Reg 768 (Modbus 40768 0-based)"),
        (client_read_ir, 767, "Input Reg 767 (Modbus 30768 1-based)"),
        (client_read_ir, 768, "Input Reg 768 (Modbus 30768 0-based)"),
        (client_read_hr, 40768, "Holding Reg 40768 (Literal)"),
        (client_read_hr, 40767, "Holding Reg 40767 (Literal 0-based)"),
        (client_read_ir, 40768, "Input Reg 40768 (Literal)"),
    ]

    active_read_fn = None
    active_address = None

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
                logger.info("Connected to Selec PLC successfully.")

            t0 = time.perf_counter()

            # 1. Read Discrete Inputs (FC 02)
            try:
                di_resp = await call_modbus(client.read_discrete_inputs, address=0, count=8, unit_id=PLC_UNIT_ID)
                if not di_resp.isError():
                    state["discrete_inputs"] = [1 if b else 0 for b in di_resp.bits[:8]]
            except Exception:
                pass

            # 2. Read IW0 Register
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
                for fn, addr, desc in candidate_list:
                    try:
                        resp = await fn(client, addr, PLC_UNIT_ID)
                        if not resp.isError() and hasattr(resp, "registers") and resp.registers:
                            val_found = resp.registers[0]
                            active_read_fn = fn
                            active_address = addr
                            state["address_detected"] = f"{addr} ({desc})"
                            logger.info(f"Locked onto IW0 at {desc} -> Value: {val_found}")
                            break
                    except Exception:
                        continue

            t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if val_found is not None:
                # Convert to signed 16-bit integer if needed (e.g. 0xFFFF -> -1)
                raw_int16 = val_found if val_found < 32768 else val_found - 65536
                state["iw0_value"] = raw_int16
                state["rtt_ms"] = round(t_elapsed_ms, 1)
                state["connected"] = True
                now_str = datetime.now().strftime("%H:%M:%S")
                state["last_update"] = now_str

                # Keep last 50 historical points for live trend chart
                state["history"].append({"time": now_str, "value": raw_int16})
                if len(state["history"]) > 50:
                    state["history"].pop(0)

            # Broadcast to connected WebSocket clients
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

        await asyncio.sleep(0.2)  # 5 Hz update rate


async def client_read_hr(client, address, unit_id):
    return await call_modbus(client.read_holding_registers, address=address, count=1, unit_id=unit_id)


async def client_read_ir(client, address, unit_id):
    return await call_modbus(client.read_input_registers, address=address, count=1, unit_id=unit_id)


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
  <title>Selec PLC - IW0 Live Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #111827;
      --border: #1f2937;
      --cyan: #06b6d4;
      --green: #10b981;
      --red: #ef4444;
      --text: #f9fafb;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .container {
      width: 100%;
      max-width: 900px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 {
      font-size: 24px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .badge.online {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: var(--green);
    }
    .badge.offline {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: var(--red);
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
      padding: 24px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.4);
    }
    .hero-metric {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 40px 20px;
      position: relative;
      overflow: hidden;
    }
    .hero-metric::before {
      content: '';
      position: absolute;
      top: -50%;
      left: 50%;
      transform: translateX(-50%);
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, rgba(6, 182, 212, 0.15) 0%, transparent 70%);
      pointer-events: none;
    }
    .metric-label {
      font-size: 14px;
      font-weight: 600;
      color: var(--cyan);
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 8px;
    }
    .metric-value {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 96px;
      font-weight: 800;
      color: #fff;
      line-height: 1;
      text-shadow: 0 0 20px rgba(6, 182, 212, 0.4);
    }
    .metric-sub {
      font-size: 14px;
      color: var(--text-muted);
      margin-top: 14px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }
    .stat-box {
      background: rgba(0,0,0,0.25);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }
    .stat-title {
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      margin-bottom: 6px;
    }
    .stat-val {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
      font-family: monospace;
    }
    .di-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 8px;
    }
    .di-pill {
      font-size: 12px;
      padding: 6px 12px;
      border-radius: 6px;
      font-weight: 600;
      background: #1f2937;
      color: #6b7280;
      border: 1px solid #374151;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .di-pill.active {
      background: rgba(16, 185, 129, 0.2);
      color: var(--green);
      border-color: rgba(16, 185, 129, 0.5);
    }
    .chart-container {
      position: relative;
      height: 250px;
      width: 100%;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Selec MiBRX-6M PLC</h1>
        <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">
          Input Register <strong>IW0 (Address 40768)</strong> &bull; Integer Format
        </div>
      </div>
      <div id="conn-badge" class="badge offline">
        <span class="dot"></span>
        <span id="conn-text">CONNECTING...</span>
      </div>
    </header>

    <!-- Hero Value Card -->
    <div class="card hero-metric">
      <div class="metric-label">PLC Input Address IW0 (Integer)</div>
      <div class="metric-value" id="iw0-display">--</div>
      <div class="metric-sub" id="lock-info">Target: 192.168.1.50:502 (Modbus Slave ID 1)</div>
    </div>

    <!-- Live Trend Chart -->
    <div class="card">
      <div style="font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--cyan);">
        Live Telemetry Trend (IW0)
      </div>
      <div class="chart-container">
        <canvas id="trendChart"></canvas>
      </div>
    </div>

    <!-- Quick Stats Grid -->
    <div class="grid">
      <div class="stat-box">
        <div class="stat-title">Modbus Target</div>
        <div class="stat-val" id="target-display">192.168.1.50:502</div>
      </div>
      <div class="stat-box">
        <div class="stat-title">Detected Register</div>
        <div class="stat-val" id="addr-display">Scanning...</div>
      </div>
      <div class="stat-box">
        <div class="stat-title">Modbus TCP RTT</div>
        <div class="stat-val" id="rtt-display">-- ms</div>
      </div>
      <div class="stat-box">
        <div class="stat-title">Last Poll</div>
        <div class="stat-val" id="time-display">--:--:--</div>
      </div>
    </div>

    <!-- Discrete Inputs Status -->
    <div class="card">
      <div style="font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--cyan);">
        Discrete Inputs (FC 02)
      </div>
      <div class="di-row" id="di-container">
        <!-- Rendered dynamically -->
      </div>
    </div>
  </div>

  <script>
    const labels = ["Belt Slip", "Pusher Ext", "Pusher Ret", "VFD Run", "VFD Fault", "E-Stop", "Guard Closed", "Optical Sensor"];
    const diContainer = document.getElementById("di-container");
    labels.forEach((lbl, idx) => {
      const el = document.createElement("div");
      el.id = "di-" + idx;
      el.className = "di-pill";
      el.innerHTML = '<span style="width:6px; height:6px; border-radius:50%; background:currentColor;"></span> ' + lbl;
      diContainer.appendChild(el);
    });

    // Initialize Chart.js
    const ctx = document.getElementById('trendChart').getContext('2d');
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'IW0 Value',
          data: [],
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.1)',
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#9ca3af', maxTicksLimit: 8 }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#9ca3af' }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });

    // WebSocket connection
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let ws;

    function connect() {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        console.log("WebSocket connected.");
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUI(data);
      };
      ws.onclose = () => {
        const badge = document.getElementById("conn-badge");
        badge.className = "badge offline";
        document.getElementById("conn-text").innerText = "DISCONNECTED";
        setTimeout(connect, 1000);
      };
    }

    function updateUI(data) {
      const badge = document.getElementById("conn-badge");
      const connText = document.getElementById("conn-text");
      if (data.connected) {
        badge.className = "badge online";
        connText.innerText = "PLC ONLINE (" + data.rtt_ms + " ms)";
      } else {
        badge.className = "badge offline";
        connText.innerText = "PLC OFFLINE";
      }

      document.getElementById("iw0-display").innerText = data.iw0_value !== undefined ? data.iw0_value : "--";
      document.getElementById("target-display").innerText = data.plc_host + ":" + data.plc_port;
      document.getElementById("addr-display").innerText = data.address_detected || "Scanning...";
      document.getElementById("rtt-display").innerText = data.rtt_ms + " ms";
      document.getElementById("time-display").innerText = data.last_update || "--";

      if (data.address_detected) {
        document.getElementById("lock-info").innerText = "Locked on: " + data.address_detected;
      }

      // Discrete Inputs
      if (data.discrete_inputs) {
        data.discrete_inputs.forEach((val, idx) => {
          const pill = document.getElementById("di-" + idx);
          if (pill) {
            if (val === 1) {
              pill.className = "di-pill active";
            } else {
              pill.className = "di-pill";
            }
          }
        });
      }

      // Chart update
      if (data.history && data.history.length > 0) {
        chart.data.labels = data.history.map(h => h.time);
        chart.data.datasets[0].data = data.history.map(h => h.value);
        chart.update();
      }
    }

    connect();
  </script>
</body>
</html>
"""


def main():
    port = int(os.getenv("PORT", 8080))
    print(f"\n=======================================================")
    print(f" Selec MiBRX-6M IW0 (Address 40768) Simple Dashboard")
    print(f" Target PLC: {PLC_HOST}:{PLC_PORT} | Unit ID: {PLC_UNIT_ID}")
    print(f" Web Interface: http://localhost:{port}")
    print(f"=======================================================\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
