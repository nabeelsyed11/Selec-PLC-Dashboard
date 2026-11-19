#!/usr/bin/env python3
"""Verify PLC is reachable and Modbus port is open."""
import socket
import sys

PLC_IP = "192.168.1.50"
PLC_PORT = 502

print("=" * 60)
print("PLC CONNECTIVITY VERIFICATION")
print("=" * 60)

# Test 1: Ping
print(f"\n[1] Ping test to {PLC_IP}...")
import subprocess
result = subprocess.run(["ping", "-n", "2", PLC_IP], capture_output=True, text=True, timeout=5)
if "TTL" in result.stdout:
    print("    ✓ PLC is alive and responding")
else:
    print("    ✗ Ping failed")
    sys.exit(1)

# Test 2: TCP port 502
print(f"\n[2] TCP connection test to {PLC_IP}:{PLC_PORT}...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex((PLC_IP, PLC_PORT))
    sock.close()
    if result == 0:
        print(f"    ✓ Modbus TCP port {PLC_PORT} is OPEN")
    else:
        print(f"    ✗ Port {PLC_PORT} is closed (error {result})")
        sys.exit(1)
except Exception as e:
    print(f"    ✗ Socket error: {e}")
    sys.exit(1)

# Test 3: Local network config
print(f"\n[3] Local network configuration...")
result = subprocess.run(["ipconfig"], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if 'IPv4' in line or 'Ethernet adapter' in line:
        print(f"    {line.strip()}")

print("\n" + "=" * 60)
print("RESULT: PLC is fully reachable!")
print("You can now use PHYSICAL mode in the dashboard.")
print("=" * 60)