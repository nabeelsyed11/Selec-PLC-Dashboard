"""
System Diagnostics and Edge Gateway Telemetry Endpoints.
"""
from fastapi import APIRouter
from app.machine.state import machine_state_manager

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/telemetry")
async def get_system_telemetry():
    """Returns Raspberry Pi 5 resource telemetry (CPU, RAM, disk, uptime)."""
    return machine_state_manager.get_system_telemetry()


@router.get("/diagnostics")
async def get_modbus_diagnostics():
    """Returns low-level Modbus TCP connection and packet statistics."""
    from app.main import app_state
    return app_state.modbus_client.diagnostics.get_summary()
