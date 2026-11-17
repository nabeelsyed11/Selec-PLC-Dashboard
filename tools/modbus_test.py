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
from app.plc.modbus_client import call_modbus


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

    # 1. Read Discrete Inputs (FC 02) with FC 01 fallback
    print(f"[*] Reading Discrete Inputs (FC 02) from address 0 to 7...")
    t_req = time.perf_counter()
    try:
        di_resp = await call_modbus(client.read_discrete_inputs, address=0, count=8, unit_id=unit_id)
        rtt_di = (time.perf_counter() - t_req) * 1000.0
        if di_resp.isError():
            print(f"  [!] Modbus Exception on FC 02: {di_resp}. Trying FC 01 (Read Coils)...")
            coils_resp = await call_modbus(client.read_coils, address=0, count=8, unit_id=unit_id)
            if not coils_resp.isError():
                print(f"  [+] FC 01 (Coils) succeeded! Bits: {coils_resp.bits[:8]}")
            else:
                print(f"  [!] FC 01 also failed: {coils_resp}")
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
        hr_resp = await call_modbus(client.read_holding_registers, address=start_reg, count=count, unit_id=unit_id)
        rtt_hr = (time.perf_counter() - t_req) * 1000.0
        if hr_resp.isError():
            print(f"  [!] Modbus Exception on FC 03: {hr_resp}. Trying FC 04 (Input Registers)...")
            ir_resp = await call_modbus(client.read_input_registers, address=start_reg, count=count, unit_id=unit_id)
            if not ir_resp.isError():
                print(f"  [+] FC 04 (Input Registers) succeeded! Regs: {ir_resp.registers[:count]}")
            else:
                print(f"  [!] FC 04 also failed: {ir_resp}")
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

    # 3. Dedicated Probe for PLC Input Address IW0 (Modbus 40768)
    print(f"\n[*] Probing PLC Input Address IW0 (Modbus 40768)...")
    iw0_found = False
    for addr_cand in [767, 768, 40767, 40768]:
        try:
            r = await call_modbus(client.read_holding_registers, address=addr_cand, count=1, unit_id=unit_id)
            if not r.isError() and hasattr(r, "registers") and r.registers:
                val = r.registers[0]
                s_val = val if val < 32768 else val - 65536
                print(f"  [+] FC 03 Succeeded at Address {addr_cand} -> IW0 Value: {s_val} (HEX: 0x{val:04X})")
                iw0_found = True
                break
            else:
                r4 = await call_modbus(client.read_input_registers, address=addr_cand, count=1, unit_id=unit_id)
                if not r4.isError() and hasattr(r4, "registers") and r4.registers:
                    val = r4.registers[0]
                    s_val = val if val < 32768 else val - 65536
                    print(f"  [+] FC 04 Succeeded at Address {addr_cand} -> IW0 Value: {s_val} (HEX: 0x{val:04X})")
                    iw0_found = True
                    break
        except Exception:
            pass

    if not iw0_found:
        print(f"  [-] Address 767/768/40768 not responding on default probe.")

    client.close()
    print(f"\n[+] Diagnostic test completed successfully.\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Selec MiBRX-6M Modbus TCP Safe Read Tester")
    parser.add_argument("--host", default="192.168.1.50", help="PLC IP address (default: 192.168.1.50)")
    parser.add_argument("--port", type=int, default=502, help="Modbus TCP port (default: 502)")
    parser.add_argument("--unit", type=int, default=1, help="Modbus Slave ID (default: 1)")
    parser.add_argument("--start", type=int, default=0, help="Starting holding register (default: 0)")
    parser.add_argument("--count", type=int, default=25, help="Number of registers to read (default: 25)")
    args = parser.parse_args()

    asyncio.run(test_modbus_connection(args.host, args.port, args.unit, args.start, args.count))


if __name__ == "__main__":
    main()
