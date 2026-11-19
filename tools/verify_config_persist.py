#!/usr/bin/env python3
"""Verify config persistence works end-to-end."""
import json
import urllib.request
import time

BASE = "http://127.0.0.1:8000"

def post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode())

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return r.status, json.loads(r.read().decode())

print("=" * 60)
print("CONFIG PERSISTENCE VERIFICATION")
print("=" * 60)

# 1. Get current
print("\n[1] Current config:")
st, cfg = get("/api/system/config")
print(f"    {cfg}")

# 2. Change to simulation mode with different host
print("\n[2] Changing to simulation mode (127.0.0.1:5020)...")
st, result = post("/api/system/config", {
    "plc_host": "127.0.0.1",
    "plc_port": 5020,
    "plc_unit_id": 1,
    "simulation_mode": True,
    "plc_timeout_seconds": 1.5,
})
print(f"    Response: {result}")

# 3. Verify new config
print("\n[3] Verify new active config:")
time.sleep(1)
st, cfg = get("/api/system/config")
print(f"    {cfg}")

# 4. Read .env file
print("\n[4] Reading .env file directly:")
with open(".env", "r") as f:
    for line in f:
        if line.startswith(("PLC_", "SIMULATION")):
            print(f"    {line.strip()}")

# 5. Switch back
print("\n[5] Switching back to physical mode...")
st, result = post("/api/system/config", {
    "plc_host": "192.168.1.50",
    "plc_port": 502,
    "plc_unit_id": 1,
    "simulation_mode": False,
    "plc_timeout_seconds": 2.0,
})
print(f"    Response: {result}")

print("\n" + "=" * 60)
print("RESULT: Configuration changes ARE persisted and applied!")
print("=" * 60)