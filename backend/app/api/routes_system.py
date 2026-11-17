"""
System Diagnostics, Edge Gateway Telemetry, and Dynamic PLC Configuration Endpoints.
"""
import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pymodbus.client import AsyncModbusTcpClient

from app.core.config import settings, BASE_DIR
from app.plc.modbus_client import call_modbus
from app.machine.state import machine_state_manager

logger = logging.getLogger("api.system")

router = APIRouter(prefix="/api/system", tags=["System"])


class PLCConfigSchema(BaseModel):
    plc_host: str = Field(..., description="IP address or hostname of Selec PLC (e.g. 192.168.1.50)")
    plc_port: int = Field(502, description="Modbus TCP Port (default 502)")
    plc_unit_id: int = Field(1, description="Modbus Slave / Unit ID (default 1)")
    simulation_mode: bool = Field(False, description="Enable virtual mock PLC simulation")
    plc_timeout_seconds: float = Field(1.5, description="Socket response timeout in seconds")


class PLCTestRequest(BaseModel):
    plc_host: str = Field(..., description="Target PLC IP address to test")
    plc_port: int = Field(502, description="Target Modbus TCP Port")
    plc_unit_id: int = Field(1, description="Target Slave ID")
    timeout_seconds: float = Field(2.0, description="Test connection timeout")


def _update_env_file(updates: Dict[str, Any]):
    """Persists updated configuration keys into the root .env file."""
    env_path = BASE_DIR / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    keys_found = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        matched_key = None
        for k in updates.keys():
            if stripped.startswith(f"{k}=") or stripped.startswith(f"{k} ="):
                matched_key = k
                break
        if matched_key:
            val = str(updates[matched_key]).lower() if isinstance(updates[matched_key], bool) else str(updates[matched_key])
            new_lines.append(f"{matched_key}={val}\n")
            keys_found.add(matched_key)
        else:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in keys_found:
            val = str(v).lower() if isinstance(v, bool) else str(v)
            new_lines.append(f"{k}={val}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    logger.info(f"Updated .env file with {list(updates.keys())}")


@router.get("/telemetry")
async def get_system_telemetry():
    """Returns Raspberry Pi 5 resource telemetry (CPU, RAM, disk, uptime)."""
    return machine_state_manager.get_system_telemetry()


@router.get("/diagnostics")
async def get_modbus_diagnostics():
    """Returns low-level Modbus TCP connection and packet statistics."""
    from app.main import app_state
    return app_state.modbus_client.diagnostics.get_summary()


@router.get("/config")
async def get_plc_config():
    """Returns active PLC network configuration and live connection state."""
    from app.main import app_state
    return {
        "plc_host": app_state.modbus_client.host,
        "plc_port": app_state.modbus_client.port,
        "plc_unit_id": app_state.modbus_client.unit_id,
        "simulation_mode": app_state.modbus_client.simulation_mode,
        "plc_timeout_seconds": app_state.modbus_client.timeout,
        "connected": app_state.modbus_client.diagnostics.connected,
    }


@router.post("/test-connection")
async def test_plc_connection(req: PLCTestRequest):
    """
    Safely tests socket connectivity and Modbus communication against the target IP/port
    without altering active gateway monitoring loops.
    """
    client = AsyncModbusTcpClient(req.plc_host, port=req.plc_port, timeout=req.timeout_seconds)
    t0 = time.perf_counter()
    try:
        connected = await asyncio.wait_for(client.connect(), timeout=req.timeout_seconds)
        if not connected:
            return {
                "success": False,
                "message": f"Connection refused or timed out connecting to {req.plc_host}:{req.plc_port}. Check IP, subnet, and PLC power.",
                "rtt_ms": None,
            }
        
        # Test reading holding register 0 (or 1 in case of 1-based addressing)
        r_resp = None
        used_addr = 0
        for test_addr in [0, 1]:
            try:
                test_r = await asyncio.wait_for(
                    call_modbus(client.read_holding_registers, address=test_addr, count=1, unit_id=req.plc_unit_id),
                    timeout=req.timeout_seconds,
                )
                if not test_r.isError():
                    r_resp = test_r
                    used_addr = test_addr
                    break
                elif r_resp is None:
                    r_resp = test_r
            except Exception:
                pass

        if r_resp is None:
            try:
                r_resp = await asyncio.wait_for(
                    call_modbus(client.read_input_registers, address=0, count=1, unit_id=req.plc_unit_id),
                    timeout=req.timeout_seconds,
                )
            except Exception:
                pass

        t_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        client.close()

        if r_resp is not None and not r_resp.isError() and hasattr(r_resp, "registers"):
            return {
                "success": True,
                "message": f"Successfully connected to Selec PLC at {req.plc_host}:{req.plc_port}! (RTT: {t_elapsed_ms:.1f} ms, Reg {used_addr}={r_resp.registers[0]})",
                "rtt_ms": round(t_elapsed_ms, 2),
                "has_exception": False,
            }

        if r_resp is not None and r_resp.isError():
            return {
                "success": True,
                "message": f"TCP connected in {t_elapsed_ms:.1f}ms! PLC responded with Modbus Exception: {r_resp}. Check Unit ID or register map.",
                "rtt_ms": round(t_elapsed_ms, 2),
                "has_exception": True,
            }

        return {
            "success": True,
            "message": f"TCP connection to {req.plc_host}:{req.plc_port} succeeded in {t_elapsed_ms:.1f}ms!",
            "rtt_ms": round(t_elapsed_ms, 2),
            "has_exception": False,
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": f"Timeout ({req.timeout_seconds}s) attempting to reach {req.plc_host}:{req.plc_port}. Check network cable & routing.",
            "rtt_ms": None,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing PLC connection: {str(e)}",
            "rtt_ms": None,
        }
    finally:
        try:
            client.close()
        except Exception:
            pass


@router.post("/config")
async def update_plc_config(cfg: PLCConfigSchema):
    """
    Updates running PLC network parameters on the fly, reconnects the Modbus client,
    and saves settings permanently to the .env file.
    """
    from app.main import app_state, start_physics_task, stop_physics_task

    # 1. Update runtime Settings object
    settings.PLC_HOST = cfg.plc_host.strip()
    settings.PLC_PORT = cfg.plc_port
    settings.PLC_UNIT_ID = cfg.plc_unit_id
    settings.SIMULATION_MODE = cfg.simulation_mode
    settings.PLC_TIMEOUT_SECONDS = cfg.plc_timeout_seconds

    # 2. Persist to .env file
    try:
        _update_env_file({
            "PLC_HOST": settings.PLC_HOST,
            "PLC_PORT": settings.PLC_PORT,
            "PLC_UNIT_ID": settings.PLC_UNIT_ID,
            "SIMULATION_MODE": settings.SIMULATION_MODE,
            "PLC_TIMEOUT_SECONDS": settings.PLC_TIMEOUT_SECONDS,
        })
    except Exception as e:
        logger.warning(f"Could not persist config to .env: {e}")

    # 3. Synchronize simulation physics engine
    if cfg.simulation_mode:
        start_physics_task()
    else:
        stop_physics_task()

    # 4. Reconfigure active Modbus client
    connected = await app_state.modbus_client.reconfigure(
        host=settings.PLC_HOST,
        port=settings.PLC_PORT,
        unit_id=settings.PLC_UNIT_ID,
        simulation_mode=settings.SIMULATION_MODE,
        timeout=settings.PLC_TIMEOUT_SECONDS,
    )

    return {
        "success": True,
        "message": f"Configuration updated successfully! {'Connected to PLC.' if connected else 'Reconnecting in background...'}",
        "config": {
            "plc_host": settings.PLC_HOST,
            "plc_port": settings.PLC_PORT,
            "plc_unit_id": settings.PLC_UNIT_ID,
            "simulation_mode": settings.SIMULATION_MODE,
            "plc_timeout_seconds": settings.PLC_TIMEOUT_SECONDS,
            "connected": connected,
        },
    }
