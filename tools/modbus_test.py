#!/usr/bin/env python3
"""
Selec MiBRX-6M Modbus TCP Communication & Discovery Test Utility
SAFE READ-ONLY UTILITY: Strictly tests read operations (FC 02 / FC 03).
Never issues writes during discovery.
"""
import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from pymodbus.client import AsyncModbusTcpClient
from app.plc.decoder import decode_16bit_uint, decode_32bit_uint, decode_32bit_float


async def test_modbus_connection(host: str, port: int, unit_id: int, start_reg: int, count: int):
    print(f"\n=======================================================")
    print(f" Selec MiBRX-6M Modbus TCP Diagnostic & Read Tool")
    print(f" Target: {host}:{port} | Slave ID: {unit_id}")
    print(f" Mode: SAFE READ-ONLY (No writes will be performed)")
    print(f"=======================================================\n")

    client = AsyncModbusTcpClient(host, port=port, timeout=2.0)
    print(f"[*] Attempting TCP connection to {host}:{port}...")
    t0 = time.perf_counter()
    try:
        connected = await client.connect()
    except Exception as e:
        print(f"[!] Socket error: {e}")
        return 1

    connect_time_ms = (time.perf_counter() - t0) * 1000.0

    if not connected:
        print(f"[!] Connection failed! Check IP address, subnet, cable, and PLC power.")
        return 1

    print(f"[+] Connected successfully in {connect_time_ms:.2f} ms\n")

    # 1. Read Discrete Inputs (FC 02)
    print(f"[*] Reading Discrete Inputs (FC 02) from address 0 to 7...")
    t_req = time.perf_counter()
    try:
        di_resp = await client.read_discrete_inputs(address=0, count=8, slave=unit_id)
        rtt_di = (time.perf_counter() - t_req) * 1000.0
        if di_resp.isError():
            print(f"  [!] Modbus Exception on FC 02: {di_resp}")
        else:
            print(f"  [+] FC 02 Response received in {rtt_di:.2f} ms:")
            names = [
                "Belt Slip Sensor", "Pusher Extended", "Pusher Retracted",
                "VFD Running", "VFD Fault", "E-Stop Healthy",
                "Guard Closed", "Optical Part Sensor"
            ]
            for idx, bit in enumerate(di_resp.bits[:8]):
                label = names[idx] if idx < len(names) else f"Input {idx}"
                state_str = "ACTIVE (1)" if bit else "INACTIVE (0)"
                print(f"      Bit {idx} ({label}): {state_str}")
    except Exception as e:
        print(f"  [!] Exception reading discrete inputs: {e}")

    # 2. Read Holding Registers (FC 03)
    print(f"\n[*] Reading Holding Registers (FC 03) from address {start_reg} to {start_reg + count - 1}...")
    t_req = time.perf_counter()
    try:
        hr_resp = await client.read_holding_registers(address=start_reg, count=count, slave=unit_id)
        rtt_hr = (time.perf_counter() - t_req) * 1000.0
        if hr_resp.isError():
            print(f"  [!] Modbus Exception on FC 03: {hr_resp}")
        else:
            print(f"  [+] FC 03 Response received in {rtt_hr:.2f} ms:")
            regs = hr_resp.registers
            for i, val in enumerate(regs):
                addr = start_reg + i
                hex_str = f"0x{val:04X}"
                print(f"      Reg {addr:02d} (40{addr+1:03d}): {val:6d} ({hex_str})")

            # Sample known decodings if starting from address 0
            if start_reg == 0 and len(regs) >= 20:
                print(f"\n  --- Decoded Engineering Estimates ---")
                load_kg = regs[0] * 0.1
                temp_c = regs[1] * 0.1
                enc_count = (regs[2] << 16) | regs[3]
                speed_mps = regs[4] * 0.01
                prod_total = (regs[5] << 16) | regs[6]
                print(f"  * Load Cell Weight : {load_kg:.1f} kg")
                print(f"  * Motor Temperature: {temp_c:.1f} °C")
                print(f"  * Encoder Pulses   : {enc_count} pulses")
                print(f"  * Belt Speed       : {speed_mps:.2f} m/s")
                print(f"  * Production Total : {prod_total} units")
    except Exception as e:
        print(f"  [!] Exception reading holding registers: {e}")

    client.close()
    print(f"\n[+] Diagnostic test completed successfully.\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Selec MiBRX-6M Modbus TCP Safe Read Tester")
    parser.add_argument("--host", default="127.0.0.1", help="PLC IP address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5020, help="Modbus TCP port (default: 5020)")
    parser.add_argument("--unit", type=int, default=1, help="Modbus Slave ID (default: 1)")
    parser.add_argument("--start", type=int, default=0, help="Starting holding register (default: 0)")
    parser.add_argument("--count", type=int, default=25, help="Number of registers to read (default: 25)")
    args = parser.parse_args()

    asyncio.run(test_modbus_connection(args.host, args.port, args.unit, args.start, args.count))


if __name__ == "__main__":
    main()
