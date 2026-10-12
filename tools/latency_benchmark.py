#!/usr/bin/env python3
"""
Selec MiBRX-6M High-Precision Latency Benchmark & CSV Exporter CLI
Measures Modbus TCP round-trip, ingestion overhead, and update intervals.
Exports raw timing observations and percentiles (P50, P95, P99) to CSV.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.plc.register_map import load_register_map
from app.plc.modbus_client import SelecModbusClient
from app.latency.monitor import LatencySubsystem
from app.core.config import settings


async def run_benchmark(duration_sec: int, output_csv: str, group: str):
    print("\n=======================================================")
    print(" Industrial IoT Latency Benchmark & Profiler")
    print(f" Target: {settings.PLC_HOST}:{settings.PLC_PORT}")
    print(f" Duration: {duration_sec} seconds | Target Group: {group}")
    print("=======================================================\n")

    reg_map = load_register_map(settings.REGISTER_MAP_PATH)
    client = SelecModbusClient(reg_map)
    subsystem = LatencySubsystem()

    connected = await client.connect()
    if not connected:
        print("[!] Failed to establish Modbus connection.")
        return 1

    subsystem.start_benchmark(duration_sec=duration_sec, group=group)
    print(f"[*] Benchmark underway... collecting timing samples.")

    start_time = time.perf_counter()
    sample_count = 0

    try:
        while (time.perf_counter() - start_time) < duration_sec:
            t_req_mono = time.perf_counter()
            t_req_iso = datetime.now(timezone.utc).isoformat()

            # Execute poll
            success = await client._poll_group(group)
            t_resp_mono = time.perf_counter()
            t_resp_iso = datetime.now(timezone.utc).isoformat()
            t_ingest_mono = time.perf_counter()
            t_ingest_iso = datetime.now(timezone.utc).isoformat()

            if success:
                sample_count += 1
                subsystem.record_poll(
                    group_name=group,
                    t_request_mono=t_req_mono,
                    t_response_mono=t_resp_mono,
                    t_ingest_mono=t_ingest_mono,
                    t_request_iso=t_req_iso,
                    t_response_iso=t_resp_iso,
                    t_ingest_iso=t_ingest_iso,
                )

            # Sleep targeted interval
            interval = reg_map.polling_groups.get(group, {}).interval_ms if hasattr(reg_map.polling_groups.get(group), 'interval_ms') else 200
            elapsed = time.perf_counter() - t_req_mono
            sleep_time = max(0.01, (interval / 1000.0) - elapsed)
            await asyncio.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[!] Benchmark interrupted by user.")
    finally:
        await client.disconnect()

    subsystem.stop_benchmark()
    csv_data = subsystem.export_benchmark_csv()

    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(csv_data)

    stats = subsystem.get_all_group_stats().get("groups", {}).get(group, {})
    print(f"\n[+] Benchmark finished! {sample_count} samples collected.")
    print(f"=======================================================")
    print(f" Modbus Round-Trip Time (RTT) Statistics:")
    print(f"   Mean RTT     : {stats.get('rtt_mean_ms', 0):.2f} ms")
    print(f"   Median (P50) : {stats.get('rtt_p50_ms', 0):.2f} ms")
    print(f"   95th % (P95) : {stats.get('rtt_p95_ms', 0):.2f} ms")
    print(f"   99th % (P99) : {stats.get('rtt_p99_ms', 0):.2f} ms")
    print(f"   Min / Max    : {stats.get('rtt_min_ms', 0):.2f} ms / {stats.get('rtt_max_ms', 0):.2f} ms")
    print(f"   Poll Jitter  : {stats.get('jitter_ms', 0):.2f} ms")
    print(f"   Ingestion Del: {stats.get('ingest_mean_ms', 0):.3f} ms")
    print(f"=======================================================")
    print(f"[+] Full raw observations saved to: {out_path.resolve()}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Industrial IoT Latency Benchmark Tool")
    parser.add_argument("--duration", type=int, default=15, help="Duration in seconds (default: 15)")
    parser.add_argument("--group", default="fast_group", help="Polling group to benchmark (default: fast_group)")
    parser.add_argument("--out", default="data/latency_benchmark.csv", help="Output CSV path (default: data/latency_benchmark.csv)")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.duration, args.out, args.group))


if __name__ == "__main__":
    main()
