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
        e_stop_ok: bool,
        vfd_running: bool,
        vfd_fault: bool,
        belt_speed_mps: float,
        has_critical_alarm: bool,
    ) -> str:
        """
        Calculates aggregate machine status:
        - COMM_LOST: Modbus connection broken or stale data
        - FAULTED: E-Stop tripped, VFD faulted, or critical safety alarm
        - RUNNING: Drive running and conveyor in motion
        - IDLE: Powered and ready, but drive stopped
        - STOPPED: Safety guard open or paused
        """
        if not comm_connected or is_stale:
            return "COMM_LOST"
        if not e_stop_ok or vfd_fault or has_critical_alarm:
            return "FAULTED"
        if vfd_running and belt_speed_mps > 0.05:
            return "RUNNING"
        if not vfd_running:
            return "IDLE"
        return "STOPPED"

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
