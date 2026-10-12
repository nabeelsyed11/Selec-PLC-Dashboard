"""
Dedicated Industrial Latency Decomposition and Benchmark Subsystem
Strictly distinguishes between Modbus network round-trip, edge ingestion delay,
WebSocket broadcast publishing, and browser client rendering.
"""
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import io
import csv
import numpy as np
import time
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger("latency.monitor")


@dataclass
class LatencyRecord:
    """Individual timing observation for a signal polling event."""
    group_name: str
    t_request_mono: float
    t_response_mono: float
    t_ingest_mono: float
    t_publish_mono: Optional[float] = None
    t_render_mono: Optional[float] = None
    t_sample_iso: Optional[str] = None
    t_plc_iso: Optional[str] = None
    t_request_iso: str = ""
    t_response_iso: str = ""
    t_ingest_iso: str = ""
    t_publish_iso: Optional[str] = None
    t_render_iso: Optional[str] = None

    @property
    def modbus_rtt_ms(self) -> float:
        """Modbus TCP network round-trip time: t_response - t_request."""
        return max(0.0, (self.t_response_mono - self.t_request_mono) * 1000.0)

    @property
    def ingestion_delay_ms(self) -> float:
        """Internal backend decode, scaling, and validation delay: t_ingest - t_response."""
        return max(0.0, (self.t_ingest_mono - self.t_response_mono) * 1000.0)

    @property
    def publish_delay_ms(self) -> float:
        """Server-side serialization and WebSocket broadcast delay: t_publish - t_ingest."""
        if self.t_publish_mono is None:
            return 0.0
        return max(0.0, (self.t_publish_mono - self.t_ingest_mono) * 1000.0)

    @property
    def render_delay_ms(self) -> Optional[float]:
        """WebSocket transit and browser DOM paint delay: t_render - t_publish."""
        if self.t_render_mono is None or self.t_publish_mono is None:
            return None
        return max(0.0, (self.t_render_mono - self.t_publish_mono) * 1000.0)

    @property
    def total_edge_to_client_ms(self) -> Optional[float]:
        """Total latency from Modbus response arrival to browser render."""
        if self.t_render_mono is None:
            return None
        return max(0.0, (self.t_render_mono - self.t_response_mono) * 1000.0)


class LatencyWindow:
    """Maintains a bounded sliding window of observations to calculate statistical percentiles."""

    def __init__(self, capacity: int = 2000):
        self.capacity = capacity
        self.history: deque[LatencyRecord] = deque(maxlen=capacity)
        self.last_response_mono: Optional[float] = None
        self.intervals_ms: deque[float] = deque(maxlen=capacity)

    def add(self, record: LatencyRecord):
        if self.last_response_mono is not None:
            interval = (record.t_response_mono - self.last_response_mono) * 1000.0
            self.intervals_ms.append(interval)
        self.last_response_mono = record.t_response_mono
        self.history.append(record)

    def calculate_stats(self) -> Dict[str, Any]:
        """Calculates Mean, P50 (Median), P95, P99, Min, Max, and Jitter."""
        if not self.history:
            return {
                "count": 0,
                "rtt_mean_ms": 0.0,
                "rtt_p50_ms": 0.0,
                "rtt_p95_ms": 0.0,
                "rtt_p99_ms": 0.0,
                "rtt_min_ms": 0.0,
                "rtt_max_ms": 0.0,
                "ingest_mean_ms": 0.0,
                "ingest_p95_ms": 0.0,
                "publish_mean_ms": 0.0,
                "update_interval_mean_ms": 0.0,
                "jitter_ms": 0.0,
            }

        rtts = [r.modbus_rtt_ms for r in self.history]
        ingests = [r.ingestion_delay_ms for r in self.history]
        publishes = [r.publish_delay_ms for r in self.history]

        rtt_arr = np.array(rtts)
        ingest_arr = np.array(ingests)
        pub_arr = np.array(publishes)

        interval_arr = np.array(self.intervals_ms) if self.intervals_ms else np.array([0.0])
        jitter = float(np.std(interval_arr)) if len(interval_arr) > 1 else 0.0

        return {
            "count": len(self.history),
            "rtt_mean_ms": round(float(np.mean(rtt_arr)), 3),
            "rtt_p50_ms": round(float(np.percentile(rtt_arr, 50)), 3),
            "rtt_p95_ms": round(float(np.percentile(rtt_arr, 95)), 3),
            "rtt_p99_ms": round(float(np.percentile(rtt_arr, 99)), 3),
            "rtt_min_ms": round(float(np.min(rtt_arr)), 3),
            "rtt_max_ms": round(float(np.max(rtt_arr)), 3),
            "ingest_mean_ms": round(float(np.mean(ingest_arr)), 3),
            "ingest_p95_ms": round(float(np.percentile(ingest_arr, 95)), 3),
            "publish_mean_ms": round(float(np.mean(pub_arr)), 3),
            "update_interval_mean_ms": round(float(np.mean(interval_arr)), 3),
            "jitter_ms": round(jitter, 3),
        }


class LatencySubsystem:
    """Coordinates multi-group latency observation and live benchmarking."""

    def __init__(self):
        self.groups: Dict[str, LatencyWindow] = {}
        # Active benchmark session state
        self.benchmark_active: bool = False
        self.benchmark_start_mono: float = 0.0
        self.benchmark_duration_sec: float = 60.0
        self.benchmark_target_group: str = "fast_group"
        self.benchmark_records: List[LatencyRecord] = []

    def record_poll(
        self,
        group_name: str,
        t_request_mono: float,
        t_response_mono: float,
        t_ingest_mono: float,
        t_request_iso: str,
        t_response_iso: str,
        t_ingest_iso: str,
        t_sample_iso: Optional[str] = None,
        t_plc_iso: Optional[str] = None,
    ) -> LatencyRecord:
        """Ingests a completed poll observation and updates statistics."""
        if group_name not in self.groups:
            self.groups[group_name] = LatencyWindow()

        record = LatencyRecord(
            group_name=group_name,
            t_request_mono=t_request_mono,
            t_response_mono=t_response_mono,
            t_ingest_mono=t_ingest_mono,
            t_request_iso=t_request_iso,
            t_response_iso=t_response_iso,
            t_ingest_iso=t_ingest_iso,
            t_sample_iso=t_sample_iso,
            t_plc_iso=t_plc_iso,
        )

        self.groups[group_name].add(record)

        if self.benchmark_active and (
            self.benchmark_target_group == "all" or self.benchmark_target_group == group_name
        ):
            self.benchmark_records.append(record)
            if (time.perf_counter() - self.benchmark_start_mono) >= self.benchmark_duration_sec:
                self.benchmark_active = False
                logger.info(f"Latency benchmark completed with {len(self.benchmark_records)} samples.")

        return record

    def update_publish_timestamp(self, record: LatencyRecord, t_publish_mono: float, t_publish_iso: str):
        record.t_publish_mono = t_publish_mono
        record.t_publish_iso = t_publish_iso

    def start_benchmark(self, duration_sec: float = 60.0, group: str = "fast_group"):
        """Starts a controlled benchmark acquisition session."""
        self.benchmark_records.clear()
        self.benchmark_duration_sec = duration_sec
        self.benchmark_target_group = group
        self.benchmark_start_mono = time.perf_counter()
        self.benchmark_active = True
        logger.info(f"Latency benchmark started: duration={duration_sec}s, target_group={group}")

    def stop_benchmark(self):
        self.benchmark_active = False

    def export_benchmark_csv(self) -> str:
        """Exports gathered benchmark observations into formatted CSV text."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "index",
            "group_name",
            "t_request_iso",
            "t_response_iso",
            "t_ingest_iso",
            "t_publish_iso",
            "t_render_iso",
            "modbus_rtt_ms",
            "ingestion_delay_ms",
            "publish_delay_ms",
            "render_delay_ms",
            "total_edge_to_client_ms",
        ])

        for i, rec in enumerate(self.benchmark_records):
            writer.writerow([
                i + 1,
                rec.group_name,
                rec.t_request_iso,
                rec.t_response_iso,
                rec.t_ingest_iso,
                rec.t_publish_iso or "",
                rec.t_render_iso or "",
                round(rec.modbus_rtt_ms, 3),
                round(rec.ingestion_delay_ms, 3),
                round(rec.publish_delay_ms, 3),
                round(rec.render_delay_ms, 3) if rec.render_delay_ms is not None else "",
                round(rec.total_edge_to_client_ms, 3) if rec.total_edge_to_client_ms is not None else "",
            ])

        return output.getvalue()

    def get_all_group_stats(self) -> Dict[str, Any]:
        """Returns statistical distributions for all monitored groups."""
        res = {}
        for grp_name, win in self.groups.items():
            res[grp_name] = win.calculate_stats()
        return {
            "groups": res,
            "benchmark": {
                "active": self.benchmark_active,
                "samples_collected": len(self.benchmark_records),
                "duration_seconds": self.benchmark_duration_sec,
                "elapsed_seconds": round(time.perf_counter() - self.benchmark_start_mono, 1) if self.benchmark_active else 0.0,
            }
        }


latency_subsystem = LatencySubsystem()
