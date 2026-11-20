#!/usr/bin/env python3
"""
Selec MiBRX-6M Live Modbus Register Scanner & Diagnostic Utility
Queries the physical PLC and displays all register values in both 0-based and 1-based
formats, along with both Big-Endian (ABCD) and Word-Swapped (CDAB) floating point decodes.
"""
import asyncio
import struct
import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from pymodbus.client import AsyncModbusTcpClient
import inspect


def call(method, *args, **kwargs):
    sig = inspect.signature(method)
    if "device_id" in sig.parameters:
        kwargs["device_id"] = 1
    elif "slave" in sig.parameters:
        kwargs["slave"] = 1
    else:
        kwargs["device_id"] = 1
    return method(*args, **kwargs)


async def scan(host: str = "192.168.1.50", port: int = 502, unit_id: int = 1):
    print("=" * 75)
    print(f"  Selec PLC Live Register Scanner ({host}:{port}, Unit ID: {unit_id})")
    print("=" * 75)

    client = AsyncModbusTcpClient(host, port=port, timeout=2.0)
    connected = await client.connect()
    if not connected:
        print(f"[!] FAILED: Could not connect to {host}:{port}")
        return

    print("[+] Successfully connected to PLC!\n")

    # 1. SCAN INPUT REGISTERS (3xxxx) around 766..775 (QW0..QW5)
    print("--- [1] SCANNING INPUT REGISTERS 766..775 (QW0..QW5, FC 04 & FC 03) ---")
    for addr in range(766, 776):
        # Try FC 04 (Input Registers)
        resp4 = await call(client.read_input_registers, address=addr, count=1)
        val4 = resp4.registers[0] if (not resp4.isError() and hasattr(resp4, "registers")) else "ERR"

        # Try FC 03 (Holding Registers)
        resp3 = await call(client.read_holding_registers, address=addr, count=1)
        val3 = resp3.registers[0] if (not resp3.isError() and hasattr(resp3, "registers")) else "ERR"

        note = ""
        if addr in (767, 768):
            note = "<-- QW0 (Modbus 30768) target candidate"
        elif addr in (770, 771):
            note = "<-- QW3 (Modbus 30771) target candidate"

        print(f"  Address {addr:4d}:  FC04(Input Reg) = {str(val4):>6}  |  FC03(Holding) = {str(val3):>6}   {note}")

    # 2. SCAN ELECTRICAL REGISTERS around 1540..1550 (%ID3, ID4, ID5)
    print("\n--- [2] SCANNING ELECTRICAL REGISTERS 1540..1550 (%ID3, ID4, ID5) ---")
    print("  Addr  |  Raw Regs (Hex)   |  ABCD (Standard)  |  CDAB (Word Swapped)  | Notes")
    print("  " + "-" * 70)
    for addr in range(1540, 1550):
        resp = await call(client.read_holding_registers, address=addr, count=2)
        if resp.isError() or not hasattr(resp, "registers"):
            # Try FC 04 if FC 03 failed
            resp = await call(client.read_input_registers, address=addr, count=2)

        if not resp.isError() and hasattr(resp, "registers") and len(resp.registers) >= 2:
            r1, r2 = resp.registers[0], resp.registers[1]
            try:
                f_norm = struct.unpack(">f", struct.pack(">HH", r1, r2))[0]
            except Exception:
                f_norm = float("nan")
            try:
                f_swap = struct.unpack(">f", struct.pack(">HH", r2, r1))[0]
            except Exception:
                f_swap = float("nan")

            note = ""
            if addr == 1541:
                note = "<-- 1541 (%ID3 1-based)"
            elif addr == 1542:
                note = "<-- 1542 (%ID3 0-based)"
            elif addr == 1543:
                note = "<-- 1543 (ID4 1-based)"
            elif addr == 1544:
                note = "<-- 1544 (ID4 0-based)"
            elif addr == 1545:
                note = "<-- 1545 (ID5 1-based)"
            elif addr == 1546:
                note = "<-- 1546 (ID5 0-based)"

            print(f"  {addr:4d}  | [{r1:5d}, {r2:5d}] (0x{r1:04X}, 0x{r2:04X}) | {f_norm:14.2f}    | {f_swap:14.2f}        | {note}")
        else:
            print(f"  {addr:4d}  | ERROR: {resp}")

    # 3. SCAN SCADA COILS (513..518)
    print("\n--- [3] SCANNING SCADA COILS 513..518 (Cycle 1..4, FC 01) ---")
    resp_coils = await call(client.read_coils, address=513, count=6)
    if not resp_coils.isError() and hasattr(resp_coils, "bits"):
        for i, bit in enumerate(resp_coils.bits[:6]):
            addr = 513 + i
            cycle_name = {514: "Cycle 1 (MX2)", 515: "Cycle 2 (MX3)", 516: "Cycle 3 (MX4)", 517: "Cycle 4 (MX5)"}.get(addr, "")
            print(f"  Coil {addr}: Value = {int(bit)}  {cycle_name}")
    else:
        print(f"  Coils read failed: {resp_coils}")

    client.close()
    print("\n[+] Scan complete!")


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.50"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 502
    unit = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    asyncio.run(scan(host, port, unit))
