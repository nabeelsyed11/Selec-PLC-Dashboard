#!/usr/bin/env python3
"""Complete network diagnostics for PLC connection."""
import subprocess
import re

print("=" * 60)
print("PLC NETWORK CONNECTION DIAGNOSTICS")
print("=" * 60)

# 1. Test PLC connectivity
print("\n[1/4] Testing PLC Reachability (192.168.1.50:502)...")
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("192.168.1.50", 502))
    sock.close()
    if result == 0:
        print("      ✓ PLC IS REACHABLE - Connection successful!")
    elif result == 10061:
        print("      ✗ Connection refused - PLC may be offline or wrong IP")
    else:
        print(f"      ✗ Connection error (code: {result}) - Not reachable")
except Exception as e:
    print(f"      ✗ Error: {e}")

# 2. Local network adapters
print("\n[2/4] Checking LAN Adapters...")
try:
    result = subprocess.run(["ipconfig"], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'Ethernet' in line or 'fe80://' in line or 'IPv4' in line:
            print(f"      {line.strip()}")
except:
    pass

# 3. Ping test
print("\n[3/4] Ping test to PLC IP...")
try:
    ping_result = subprocess.run(
        ["ping", "-n", "2", "192.168.1.50"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if "TTL" in ping_result.stdout or "bytes=32" in ping_result.stdout:
        print("      ✓ PLC is alive and responding to ping!")
    else:
        print("      ✗ No response from PLC")
except:
    print("      ✗ Ping command failed")

# 4. Network adapter status
print("\n[4/4] Network Adapter Status...")
try:
    result = subprocess.run(["net", "sh", "interface", "show", "interface"], capture_output=True, timeout=10)
    for line in result.stdout.decode('latin-1').split('\n'):
        if 'Ethernet' in line and 'Name' not in line:
            status = "UP" if "connected" in line.lower() else "DOWN"
            print(f"      {line.strip()} [{status}]")
except:
    pass

print("\n" + "=" * 60)
print("SUMMARY:")
print("=" * 60)
print("To fix PLC communication:")
print("1. Connect Ethernet cable between PC and PLC")
print("2. Ensure PLC power is ON")
print("3. Run: run_simulation.bat (if not ready)")
print("=" * 60)