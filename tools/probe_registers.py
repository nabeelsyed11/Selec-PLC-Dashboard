#!/usr/bin/env python3
"""
Diagnostic register probe for Selec MiBRX-6M PLC.
Scans multiple addresses, counts, and function codes to discover exact memory mapping.
"""
import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from pymodbus.client import AsyncModbusTcpClient
from app.plc.modbus_client import call_modbus


async def probe(host="192.168.1.50", port=502, unit_id=1):
    client = AsyncModbusTcpClient(host, port=port, timeout=2.0)
    connected = await client.connect()
    if not connected:
        print(f"[!] Could not connect to {host}:{port}")
        return

    print(f"[+] Connected to {host}:{port} (Unit: {unit_id})\n")

    # 1. Probe Coils (FC 01)
    print("--- [1] Probing Coils (FC 01) ---")
    for addr in [0, 1, 10, 100]:
        try:
            r = await call_modbus(client.read_coils, address=addr, count=1, unit_id=unit_id)
            if not r.isError():
                print(f"  ✅ FC 01 Coil at address {addr}: {r.bits[0]}")
            else:
                print(f"  ❌ FC 01 Coil at address {addr}: {r}")
        except Exception as e:
            print(f"  ❌ FC 01 error at {addr}: {e}")

    # 2. Probe Discrete Inputs (FC 02)
    print("\n--- [2] Probing Discrete Inputs (FC 02) ---")
    for addr in [0, 1]:
        try:
            r = await call_modbus(client.read_discrete_inputs, address=addr, count=8, unit_id=unit_id)
            if not r.isError():
                print(f"  ✅ FC 02 Inputs starting at {addr}: {r.bits[:8]}")
            else:
                print(f"  ❌ FC 02 Inputs at {addr}: {r}")
        except Exception as e:
            print(f"  ❌ FC 02 error at {addr}: {e}")

    # 3. Probe Holding Registers (FC 03) with count=1
    print("\n--- [3] Probing Holding Registers (FC 03) [count=1] ---")
    test_addrs = [0, 1, 2, 3, 4, 5, 10, 100, 1000, 40000, 40001]
    found_hr = []
    for addr in test_addrs:
        try:
            r = await call_modbus(client.read_holding_registers, address=addr, count=1, unit_id=unit_id)
            if not r.isError():
                print(f"  ✅ FC 03 Register at address {addr}: value={r.registers[0]} (0x{r.registers[0]:04X})")
                found_hr.append(addr)
            else:
                print(f"  ❌ FC 03 Register at address {addr}: {r}")
        except Exception as e:
            print(f"  ❌ FC 03 error at {addr}: {e}")

    # 4. Probe Input Registers (FC 04) with count=1
    print("\n--- [4] Probing Input Registers (FC 04) [count=1] ---")
    for addr in [0, 1, 2, 3, 10, 100, 1000, 30000, 30001]:
        try:
            r = await call_modbus(client.read_input_registers, address=addr, count=1, unit_id=unit_id)
            if not r.isError():
                print(f"  ✅ FC 04 Register at address {addr}: value={r.registers[0]} (0x{r.registers[0]:04X})")
            else:
                pass
        except Exception as e:
            pass

    client.close()
    print("\n[+] Probe complete!")


if __name__ == "__main__":
    asyncio.run(probe())
