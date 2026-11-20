"""
Machine Operating Mode Engine and Industrial Production Analytics.
Computes machine status (RUNNING, STOPPED, IDLE, FAULTED, COMM_LOST),
OEE metrics, uptime, and edge gateway resource telemetry.
"""
from datetime import datetime, timezone
import psutil
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("machine.state")


class MachineStateManager:
    """Manages high-level machine status, operating state, and edge telemetry."""

    def __init__(self):
        self.start_time_monotonic = time.perf_counter()
        self.start_time_utc = datetime.now(timezone.utc)

    def determine_machine_state(
        self,
        comm_connected: bool,
        is_stale: bool,
        e_stop_ok: bool = True,
        vfd_running: bool = False,
        vfd_fault: bool = False,
        belt_speed_mps: float = 0.0,
        has_critical_alarm: bool = False,
        cycle_active: bool = False,
        vfd_hz: float = 0.0,
    ) -> str:
        """
        Calculates aggregate machine status:
        - COMM_LOST: Modbus connection broken or stale data
        - RUNNING: Any process cycle active (MX2..MX5), or VFD frequency > 0, or drive running
        - READY: Powered and ready in standby, Modbus link healthy
        """
        if not comm_connected or is_stale:
            return "COMM_LOST"
        if cycle_active or (vfd_running and belt_speed_mps > 0.05) or (vfd_hz > 0.1) or vfd_running:
            return "RUNNING"
        return "READY"

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Edge Raspberry Pi 5 resource telemetry."""
        uptime_sec = time.perf_counter() - self.start_time_monotonic
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Raspberry Pi CPU temperature (if available on Linux /sys/class/thermal)
        cpu_temp = None
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if "cpu_thermal" in temps:
                    cpu_temp = temps["cpu_thermal"][0].current
        except Exception:
            pass

        return {
            "uptime_seconds": int(uptime_sec),
            "cpu_percent": cpu_pct,
            "memory_percent": mem.percent,
            "memory_used_mb": int(mem.used / (1024 * 1024)),
            "disk_percent": disk.percent,
            "cpu_temperature_c": cpu_temp,
            "gateway_time_utc": datetime.now(timezone.utc).isoformat(),
        }


machine_state_manager = MachineStateManager()
