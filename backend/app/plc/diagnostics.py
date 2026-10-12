"""
PLC Modbus Communication Diagnostics and Freshness Monitor
Maintains packet loss counters, exception rates, round-trip times,
and flags signals as STALE when update deadlines are violated.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Dict, List, Optional


@dataclass
class GroupDiagnostics:
    group_name: str
    target_interval_ms: int
    total_polls: int = 0
    successful_polls: int = 0
    failed_polls: int = 0
    consecutive_failures: int = 0
    last_rtt_ms: float = 0.0
    min_rtt_ms: float = float("inf")
    max_rtt_ms: float = 0.0
    avg_rtt_ms: float = 0.0
    last_poll_time_monotonic: float = 0.0
    last_successful_time_iso: Optional[str] = None
    last_error_message: Optional[str] = None

    def record_success(self, rtt_ms: float, monotonic_now: float, utc_iso: str):
        self.total_polls += 1
        self.successful_polls += 1
        self.consecutive_failures = 0
        self.last_rtt_ms = rtt_ms
        self.last_poll_time_monotonic = monotonic_now
        self.last_successful_time_iso = utc_iso
        self.last_error_message = None

        if rtt_ms < self.min_rtt_ms:
            self.min_rtt_ms = rtt_ms
        if rtt_ms > self.max_rtt_ms:
            self.max_rtt_ms = rtt_ms

        # Exponential moving average for avg_rtt
        if self.avg_rtt_ms == 0.0:
            self.avg_rtt_ms = rtt_ms
        else:
            self.avg_rtt_ms = (self.avg_rtt_ms * 0.9) + (rtt_ms * 0.1)

    def record_failure(self, error_msg: str, monotonic_now: float):
        self.total_polls += 1
        self.failed_polls += 1
        self.consecutive_failures += 1
        self.last_poll_time_monotonic = monotonic_now
        self.last_error_message = error_msg

    @property
    def packet_error_rate(self) -> float:
        if self.total_polls == 0:
            return 0.0
        return (self.failed_polls / self.total_polls) * 100.0


class CommunicationDiagnosticsManager:
    """System-wide communication statistics and health tracking."""

    def __init__(self, max_data_age_seconds: float = 3.0):
        self.max_data_age_seconds = max_data_age_seconds
        self.connected: bool = False
        self.reconnect_count: int = 0
        self.groups: Dict[str, GroupDiagnostics] = {}
        self.last_global_success_monotonic: float = 0.0

    def register_group(self, name: str, interval_ms: int):
        self.groups[name] = GroupDiagnostics(group_name=name, target_interval_ms=interval_ms)

    def is_data_stale(self, last_update_monotonic: float) -> bool:
        """Return True if time since last update exceeds max permitted age."""
        if last_update_monotonic <= 0.0:
            return True
        return (time.perf_counter() - last_update_monotonic) > self.max_data_age_seconds

    def get_summary(self) -> Dict:
        """Returns diagnostic payload for dashboard."""
        now = time.perf_counter()
        time_since_last_success = now - self.last_global_success_monotonic if self.last_global_success_monotonic > 0 else -1

        group_summaries = {}
        for name, g in self.groups.items():
            group_summaries[name] = {
                "total_polls": g.total_polls,
                "successful_polls": g.successful_polls,
                "failed_polls": g.failed_polls,
                "consecutive_failures": g.consecutive_failures,
                "error_rate_pct": round(g.packet_error_rate, 2),
                "last_rtt_ms": round(g.last_rtt_ms, 2),
                "min_rtt_ms": round(g.min_rtt_ms, 2) if g.min_rtt_ms != float("inf") else 0.0,
                "max_rtt_ms": round(g.max_rtt_ms, 2),
                "avg_rtt_ms": round(g.avg_rtt_ms, 2),
                "last_successful_time": g.last_successful_time_iso,
                "last_error": g.last_error_message,
            }

        return {
            "connected": self.connected,
            "reconnect_count": self.reconnect_count,
            "time_since_last_poll_sec": round(time_since_last_success, 2) if time_since_last_success >= 0 else None,
            "is_system_stale": time_since_last_success > self.max_data_age_seconds if time_since_last_success >= 0 else True,
            "groups": group_summaries,
        }
