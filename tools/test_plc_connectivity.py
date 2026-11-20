#!/usr/bin/env python3
"""
Selec PLC Hardware Connectivity & Modbus Register Diagnostic Tool
Works on both Raspberry Pi (Linux) and Windows.
Tests raw TCP socket and polls the real registers: 767 (IW0), 514 (MX2), 1541 (TD3).
"""
import asyncio
import os
import socket
import subprocess
import sys
import time

def check_local_network():
    """Display local network adapters and IPs."""
    print("=" * 65)
    print("  [1/4] LOCAL NETWORK CONFIGURATION")
    print("=" * 65)
    try:
        if os.name == "nt":
            res = subprocess.run(["ipconfig"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if "IPv4" in line or "Default Gateway" in line or "Ethernet adapter" in line:
                    print("  " + line.strip())
        else:
            res = subprocess.run(["ip", "-4", "addr", "show"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if "inet " in line or ": eth" in line or ": en" in line or ": wlan" in line:
                    print("  " + line.strip())
    except Exception as e:
        print(f"  Error reading local network: {e}")
    print()

def test_raw_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    """Test raw TCP connection to PLC."""
    print("=" * 65)
    print(f"  [2/4] TESTING RAW TCP SOCKET ({host}:{port})")
    print("=" * 65)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        t0 = time.perf_counter()
        rc = sock.connect_ex((host, port))
        elapsed = (time.perf_counter() - t0) * 1000.0
        sock.close()
        if rc == 0:
            print(f"  ✓ SUCCESS: TCP port {port} is open and responding in {elapsed:.1f}ms!")
            return True
        elif rc in (111, 10061):
            print(f"  ✗ FAILED: Connection refused by {host}:{port} (error code {rc}).")
            print("    Check if PLC is in RUN mode and no other software is connected.")
            return False
        else:
            print(f"  ✗ FAILED: Socket error code {rc} to {host}:{port}.")
            return False
    except socket.timeout:
        print(f"  ✗ TIMEOUT: No response from {host}:{port} within {timeout}s.")
        print("    Check Ethernet cable, subnet, or if PLC port 502 is busy.")
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False

async def test_modbus_registers(host: str, port: int, unit_id: int = 1):
    """Test reading the exact Selec SCADA registers via PyModbus."""
    print()
    print("=" * 65)
    print(f"  [3/4] TESTING MODBUS TCP REGISTERS (Unit ID: {unit_id})")
    print("=" * 65)
    try:
        from pymodbus.client import AsyncModbusTcpClient
        import inspect
    except ImportError:
        print("  ✗ pymodbus is not installed in current Python environment.")
        return

    client = AsyncModbusTcpClient(host, port=port, timeout=2.0)
    connected = await client.connect()
    if not connected:
        print(f"  ✗ Modbus client could not connect to {host}:{port}.")
        return

    print(f"  ✓ Modbus TCP client connected to {host}:{port}!")

    def call(method, *args, **kwargs):
        sig = inspect.signature(method)
        if "device_id" in sig.parameters:
            kwargs["device_id"] = unit_id
        elif "slave" in sig.parameters:
            kwargs["slave"] = unit_id
        else:
            kwargs["device_id"] = unit_id
        return method(*args, **kwargs)

    # 1. Test IW0 (Holding Register 767 or Input Register 767)
    print("\n  -- Checking Process Input IW0 (Modbus 40768) --")
    for fn, name in [(client.read_holding_registers, "Holding Reg 767 (FC 03)"),
                     (client.read_input_registers, "Input Reg 767 (FC 04)"),
                     (client.read_holding_registers, 768),
                     (client.read_input_registers, 768)]:
        addr = 767 if isinstance(name, str) else name
        label = name if isinstance(name, str) else f"Reg {addr}"
        try:
            resp = await call(fn, address=addr, count=1)
            if not resp.isError() and hasattr(resp, "registers"):
                val = resp.registers[0]
                print(f"    ✓ {label}: VALUE = {val} (raw)")
                break
            else:
                print(f"    ✗ {label}: {resp}")
        except Exception as e:
            print(f"    ✗ {label}: {e}")

    # 2. Test Coils MX2..MX5 (Coils 514..517)
    print("\n  -- Checking SCADA Cycles MX2-MX5 (Coils 514-517, FC 01) --")
    for addr in [514, 513]:
        try:
            resp = await call(client.read_coils, address=addr, count=4)
            if not resp.isError() and hasattr(resp, "bits"):
                bits = [int(b) for b in resp.bits[:4]]
                print(f"    ✓ Coils starting at {addr}: Cycle 1-4 = {bits}")
                break
            else:
                print(f"    ✗ Coils starting at {addr}: {resp}")
        except Exception as e:
            print(f"    ✗ Coils starting at {addr}: {e}")

    # 3. Test Voltage TD3 (Holding Register 1541)
    print("\n  -- Checking Mains Voltage TD3 (Holding Reg 1541, FC 03) --")
    for addr in [1541, 1542]:
        try:
            resp = await call(client.read_holding_registers, address=addr, count=2)
            if not resp.isError() and hasattr(resp, "registers"):
                print(f"    ✓ Holding Regs starting at {addr}: {resp.registers[:2]}")
                break
            else:
                print(f"    ✗ Holding Regs starting at {addr}: {resp}")
        except Exception as e:
            print(f"    ✗ Holding Regs starting at {addr}: {e}")

    client.close()

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.50"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 502
    unit = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    check_local_network()
    tcp_ok = test_raw_tcp(host, port)
    if tcp_ok:
        asyncio.run(test_modbus_registers(host, port, unit))

    print("\n" + "=" * 65)
    print("  [4/4] DIAGNOSTIC SUMMARY")
    print("=" * 65)
    if tcp_ok:
        print("  ✓ PLC socket communication is working!")
    else:
        print("  ✗ Cannot open TCP socket to PLC.")
        print("  Common causes:")
        print("   1. Another dashboard instance is already connected to the PLC in another window.")
        print("   2. PLC Ethernet is disconnected or on a different IP subnet.")
        print("   3. PLC is not in RUN mode.")
    print("=" * 65)
