"""
System Diagnostics, Edge Gateway Telemetry, and Dynamic PLC Configuration Endpoints.
"""
import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Optional, Dict, Any

import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from pymodbus.client import AsyncModbusTcpClient

from app.core.config import settings, BASE_DIR
from app.plc.modbus_client import call_modbus
from app.machine.state import machine_state_manager

logger = logging.getLogger("api.system")

router = APIRouter(prefix="/api/system", tags=["System"])

HOST_REGEX = re.compile(r"^[a-zA-Z0-9.\-_]+$")
ALLOWED_ENV_KEYS = {"PLC_HOST", "PLC_PORT", "PLC_UNIT_ID", "SIMULATION_MODE", "PLC_TIMEOUT_SECONDS"}


class PLCConfigSchema(BaseModel):
    plc_host: str = Field(..., description="IP address or hostname of Selec PLC (e.g. 192.168.1.50)")
    plc_port: int = Field(502, ge=1, le=65535, description="Modbus TCP Port (default 502)")
    plc_unit_id: int = Field(1, ge=1, le=255, description="Modbus Slave / Unit ID (default 1)")
    simulation_mode: bool = Field(False, description="Enable virtual mock PLC simulation")
    plc_timeout_seconds: float = Field(1.5, ge=0.1, le=30.0, description="Socket response timeout in seconds")
    connected: Optional[bool] = Field(None, description="Connection status indicator from UI")

    @field_validator("plc_host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned or not HOST_REGEX.match(cleaned):
            raise ValueError("Invalid host/IP address format. Newlines and special characters are not permitted.")
        return cleaned


class PLCTestRequest(BaseModel):
    plc_host: str = Field(..., description="Target PLC IP address to test")
    plc_port: int = Field(502, ge=1, le=65535, description="Target Modbus TCP Port")
    plc_unit_id: int = Field(1, ge=1, le=255, description="Target Slave ID")
    timeout_seconds: float = Field(2.0, ge=0.1, le=30.0, description="Test connection timeout")

    @field_validator("plc_host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned or not HOST_REGEX.match(cleaned):
            raise ValueError("Invalid host/IP address format. Newlines and special characters are not permitted.")
        return cleaned


def _update_env_file(updates: Dict[str, Any]):
    """Persists sanitized configuration keys into the root .env file strictly from allowlist."""
    env_path = BASE_DIR / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Filter updates to strict allowlist only
    safe_updates = {}
    for k, v in updates.items():
        if k in ALLOWED_ENV_KEYS:
            if isinstance(v, bool):
                safe_updates[k] = "true" if v else "false"
            else:
                # Strip newlines, carriage returns, and control chars
                sanitized_val = re.sub(r"[\r\n\x00-\x1f]", "", str(v)).strip()
                safe_updates[k] = sanitized_val

    keys_found = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        matched_key = None
        for k in safe_updates.keys():
            if stripped.startswith(f"{k}=") or stripped.startswith(f"{k} ="):
                matched_key = k
                break
        if matched_key:
            new_lines.append(f"{matched_key}={safe_updates[matched_key]}\n")
            keys_found.add(matched_key)
        else:
            new_lines.append(line)

    for k, v in safe_updates.items():
        if k not in keys_found:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    logger.info(f"Updated .env file with {list(safe_updates.keys())}")


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
    from app.main import app_state
    t0 = time.perf_counter()
    used_existing = False

    # If the main gateway is already connected to this target, test over the existing socket
    # to avoid single-connection PLC port contention.
    if (
        app_state.modbus_client.client
        and getattr(app_state.modbus_client.client, "connected", False)
        and app_state.modbus_client.host == req.plc_host
        and app_state.modbus_client.port == req.plc_port
        and not app_state.modbus_client.simulation_mode
    ):
        client = app_state.modbus_client.client
        used_existing = True
    else:
        client = AsyncModbusTcpClient(req.plc_host, port=req.plc_port, timeout=req.timeout_seconds)
        try:
            connected = await asyncio.wait_for(client.connect(), timeout=req.timeout_seconds)
            if not connected:
                return {
                    "success": False,
                    "message": f"Connection refused or timed out connecting to {req.plc_host}:{req.plc_port}. Ensure no other tool (e.g. simple_dashboard.py or modpoll) is holding port 502.",
                    "rtt_ms": None,
                }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": f"Timeout ({req.timeout_seconds}s) connecting to {req.plc_host}:{req.plc_port}. Check PLC power/RUN mode and ensure no other Modbus client (like simple_dashboard.py or modpoll) is holding port 502.",
                "rtt_ms": None,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error connecting to {req.plc_host}:{req.plc_port}: {e}",
                "rtt_ms": None,
            }

    try:
        # Test candidate registers: 767 (IW0 / 40768), 514 (Coil MX2), 1541 (Voltage), 0, 1
        r_resp = None
        used_addr = 767
        reg_type = "Holding Reg"

        test_candidates = [
            (client.read_holding_registers, 767, "Holding Reg 767 (Modbus 40768)"),
            (client.read_input_registers, 767, "Input Reg 767 (Modbus 30768)"),
            (client.read_coils, 514, "Coil 514 (MX2)"),
            (client.read_holding_registers, 1541, "Holding Reg 1541 (TD3)"),
            (client.read_holding_registers, 0, "Holding Reg 0"),
            (client.read_holding_registers, 1, "Holding Reg 1"),
        ]

        for fn, addr, desc in test_candidates:
            try:
                test_r = await asyncio.wait_for(
                    call_modbus(fn, address=addr, count=1, unit_id=req.plc_unit_id),
                    timeout=min(1.0, req.timeout_seconds),
                )
                if not test_r.isError():
                    r_resp = test_r
                    used_addr = addr
                    reg_type = desc
                    break
                elif r_resp is None:
                    r_resp = test_r
            except Exception:
                pass

        t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if not used_existing:
            try:
                client.close()
            except Exception:
                pass

        if r_resp is not None and not r_resp.isError():
            val = ""
            if hasattr(r_resp, "registers") and r_resp.registers:
                val = f", Value={r_resp.registers[0]}"
            elif hasattr(r_resp, "bits") and r_resp.bits:
                val = f", Bit={int(r_resp.bits[0])}"
            return {
                "success": True,
                "message": f"Successfully connected to Selec PLC at {req.plc_host}:{req.plc_port}! (RTT: {t_elapsed_ms:.1f} ms, {reg_type}{val})",
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
            "message": f"Timeout ({req.timeout_seconds}s) reading register from {req.plc_host}:{req.plc_port}. Check PLC RUN mode and Unit ID.",
            "rtt_ms": None,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing PLC connection: {str(e)}",
            "rtt_ms": None,
        }
    finally:
        if not used_existing:
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
    try:
        connected = await app_state.modbus_client.reconfigure(
            host=settings.PLC_HOST,
            port=settings.PLC_PORT,
            unit_id=settings.PLC_UNIT_ID,
            simulation_mode=settings.SIMULATION_MODE,
            timeout=settings.PLC_TIMEOUT_SECONDS,
        )
    except Exception as e:
        logger.error(f"Error reconfiguring Modbus client: {e}")
        connected = False

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
