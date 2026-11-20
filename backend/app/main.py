"""
FastAPI Main Application for Selec MiBRX-6M Industrial IoT Gateway.
Coordinates Modbus TCP polling, vibration engine, latency monitor,
alarms, database persistence, REST endpoints, and WebSocket streaming.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Dict, Any, Optional
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.plc.register_map import load_register_map
from app.plc.modbus_client import SelecModbusClient
from app.sensors.processing import SensorDataProcessor
from app.vibration.sensor import vibration_engine
from app.latency.monitor import latency_subsystem
from app.machine.state import machine_state_manager
from app.machine.alarms import alarms_manager
from app.database.session import init_db, db_buffer
from app.simulation.mock_plc import SimulatedModbusServer, global_mock_plc
from app.api.websocket import ws_manager

from app.api.routes_signals import router as signals_router
from app.api.routes_latency import router as latency_router
from app.api.routes_alarms import router as alarms_router
from app.api.routes_control import router as control_router
from app.api.routes_vibration import router as vibration_router
from app.api.routes_production import router as production_router
from app.api.routes_system import router as system_router

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("main")


class AppState:
    """Global in-memory state shared across requests and background tasks."""

    def __init__(self):
        self.reg_map = load_register_map(settings.REGISTER_MAP_PATH)
        self.modbus_client = SelecModbusClient(self.reg_map)
        self.sensor_processor = SensorDataProcessor()
        self.signals_snapshot: Dict[str, Any] = {}
        self.current_machine_state: str = "READY" if settings.SIMULATION_MODE else "COMM_LOST"
        self.simulated_server: Optional[SimulatedModbusServer] = None
        self.broadcast_task: Optional[asyncio.Task] = None
        self.physics_task: Optional[asyncio.Task] = None

        self.cycles_telemetry: Dict[str, Dict[str, Any]] = {
            "cycle_1": {
                "cycle_num": 1,
                "name": "First Cycle",
                "plc_tag": "MX2",
                "modbus_coil": 514,
                "active": False,
                "delay_ms": 0.0,
                "trigger_delay_ms": 0.0,
                "last_pressed_at": None,
            },
            "cycle_2": {
                "cycle_num": 2,
                "name": "Second Cycle",
                "plc_tag": "MX3",
                "modbus_coil": 515,
                "active": False,
                "delay_ms": 0.0,
                "trigger_delay_ms": 0.0,
                "last_pressed_at": None,
            },
            "cycle_3": {
                "cycle_num": 3,
                "name": "Third Cycle",
                "plc_tag": "MX4",
                "modbus_coil": 516,
                "active": False,
                "delay_ms": 0.0,
                "trigger_delay_ms": 0.0,
                "last_pressed_at": None,
            },
            "cycle_4": {
                "cycle_num": 4,
                "name": "Fourth Cycle",
                "plc_tag": "MX5",
                "modbus_coil": 517,
                "active": False,
                "delay_ms": 0.0,
                "trigger_delay_ms": 0.0,
                "last_pressed_at": None,
            },
        }

        # Pre-populate initial signals with honest quality flags
        init_quality = "SIMULATED" if settings.SIMULATION_MODE else "DISCONNECTED"
        for sig in self.reg_map.discrete_signals:
            self.signals_snapshot[sig.name] = {
                "name": sig.name,
                "raw_value": 0,
                "value": 0,
                "unit": "",
                "quality": init_quality,
                "group": sig.group,
            }
        for sig in self.reg_map.numerical_signals:
            self.signals_snapshot[sig.name] = {
                "name": sig.name,
                "raw_value": 0,
                "value": 0.0,
                "unit": sig.engineering_unit,
                "quality": init_quality,
                "group": sig.group,
            }


app_state = AppState()


def on_modbus_measurements(measurements: Dict[str, Any]):
    """
    Callback invoked whenever fresh Modbus measurements arrive.
    Performs unit calibration, checks alarms, updates snapshots, and buffers data.
    """
    t_ingest_mono = time.perf_counter()
    t_ingest_iso = datetime.now(timezone.utc).isoformat()

    for name, meas in measurements.items():
        # Record latency observation per group
        grp = meas.get("group", "fast_group")
        rec = latency_subsystem.record_poll(
            group_name=grp,
            t_request_mono=meas["t_request_mono"],
            t_response_mono=meas["t_response_mono"],
            t_ingest_mono=t_ingest_mono,
            t_request_iso=meas["t_request"],
            t_response_iso=meas["t_response"],
            t_ingest_iso=t_ingest_iso,
        )

        # Buffer latency record
        db_buffer.add_latency({
            "group_name": grp,
            "modbus_rtt_ms": rec.modbus_rtt_ms,
            "ingestion_delay_ms": rec.ingestion_delay_ms,
            "publish_delay_ms": rec.publish_delay_ms,
            "data_age_ms": rec.modbus_rtt_ms,
            "t_request_iso": rec.t_request_iso,
            "t_response_iso": rec.t_response_iso,
            "t_ingest_iso": rec.t_ingest_iso,
            "timestamp_utc": datetime.now(timezone.utc),
        })

        # Process specific signals
        if name == "load_cell_weight":
            meas["value"] = app_state.sensor_processor.process_load_cell(meas["raw_value"])
        elif name == "motor_temperature":
            temp_c = meas["value"]
            active, sev = app_state.sensor_processor.process_temperature(temp_c)
            if active:
                alarms_manager.trigger_alarm(
                    "MOTOR_HIGH_TEMP", sev, f"Motor temperature elevated: {temp_c:.1f} °C (Threshold: 75°C)"
                )
            elif sev == "CLEARED":
                alarms_manager.clear_alarm("MOTOR_HIGH_TEMP")
        elif name == "encoder_raw_count":
            rpm, speed = app_state.sensor_processor.process_encoder(int(meas["raw_value"]))
            app_state.signals_snapshot["encoder_roller_rpm"] = {
                "name": "encoder_roller_rpm",
                "value": rpm,
                "unit": "RPM",
                "quality": meas["quality"],
                "group": grp,
            }

        # Check belt slip
        if name == "belt_slip_sensor":
            vfd_hz = app_state.signals_snapshot.get("vfd_output_frequency", {}).get("value", 0.0)
            enc_spd = app_state.sensor_processor.current_belt_speed_mps
            slip_active, dur = app_state.sensor_processor.process_belt_slip(meas["value"], vfd_hz, enc_spd)
            if slip_active:
                alarms_manager.trigger_alarm(
                    "BELT_SLIP", "WARNING", f"Conveyor belt slip detected for {dur:.1f} seconds!"
                )
            else:
                alarms_manager.clear_alarm("BELT_SLIP")

        # Update live snapshot
        meas["delay_ms"] = round(float(meas.get("rtt_ms", 0.0)), 1)
        app_state.signals_snapshot[name] = meas
        # Buffer historical measurement (sample rate throttled to protect SD card)
        db_buffer.add_measurement(name, float(meas["value"]), meas["quality"])

    # Update SCADA Process Cycles tracking (MX2..MX5)
    cycle_mappings = [
        ("cycle_1", "cycle_1_mx2"),
        ("cycle_2", "cycle_2_mx3"),
        ("cycle_3", "cycle_3_mx4"),
        ("cycle_4", "cycle_4_mx5"),
    ]
    now_mono = time.perf_counter()
    now_iso = datetime.now(timezone.utc).strftime("%H:%M:%S")

    for cycle_key, sig_name in cycle_mappings:
        sig = app_state.signals_snapshot.get(sig_name)
        if sig and cycle_key in app_state.cycles_telemetry:
            c_data = app_state.cycles_telemetry[cycle_key]
            is_active = sig.get("value", 0) == 1
            rtt = round(float(sig.get("rtt_ms", 0.0)), 1)
            c_data["delay_ms"] = rtt

            # Capture the exact time delay it took to reach and display on dashboard when pressed
            if is_active and not c_data["active"]:
                c_data["active"] = True
                c_data["last_pressed_at"] = now_iso
                c_data["trigger_delay_ms"] = rtt if rtt > 0.0 else round(float(sig.get("delay_ms", 0.0)), 1)
            elif not is_active and c_data["active"]:
                c_data["active"] = False

    # Update overall machine state
    e_stop = app_state.signals_snapshot.get("emergency_stop_ok", {}).get("value", 1) == 1
    vfd_run = app_state.signals_snapshot.get("vfd_running_status", {}).get("value", 0) == 1
    vfd_fault = app_state.signals_snapshot.get("vfd_fault_status", {}).get("value", 0) == 1
    belt_spd = app_state.sensor_processor.current_belt_speed_mps
    is_stale = app_state.modbus_client.diagnostics.is_data_stale(
        app_state.modbus_client.diagnostics.last_global_success_monotonic
    )

    # Check SCADA Process Cycles (MX2..MX5) and VFD Frequency
    c1 = app_state.signals_snapshot.get("cycle_1_mx2", {}).get("value", 0) == 1
    c2 = app_state.signals_snapshot.get("cycle_2_mx3", {}).get("value", 0) == 1
    c3 = app_state.signals_snapshot.get("cycle_3_mx4", {}).get("value", 0) == 1
    c4 = app_state.signals_snapshot.get("cycle_4_mx5", {}).get("value", 0) == 1
    cycle_active = c1 or c2 or c3 or c4

    vfd_hz = (
        app_state.signals_snapshot.get("scaled_out_vfd_qw0", {}).get("value")
        or app_state.signals_snapshot.get("vfd_output_frequency", {}).get("value", 0.0)
        or 0.0
    )

    app_state.current_machine_state = machine_state_manager.determine_machine_state(
        comm_connected=app_state.modbus_client.diagnostics.connected,
        is_stale=is_stale,
        e_stop_ok=e_stop,
        vfd_running=vfd_run,
        vfd_fault=vfd_fault,
        belt_speed_mps=belt_spd,
        has_critical_alarm=False,
        cycle_active=cycle_active,
        vfd_hz=float(vfd_hz),
    )


async def websocket_broadcast_loop():
    """High-frequency periodic broadcast (10 Hz) of aggregated telemetry to browser clients."""
    while True:
        try:
            await asyncio.sleep(0.10)  # 10 Hz WebSocket streaming
            if ws_manager.active_connections:
                is_sim = app_state.modbus_client.simulation_mode
                is_conn = app_state.modbus_client.diagnostics.connected

                # Strict state management when physical mode is active
                if not is_sim:
                    if not is_conn:
                        app_state.current_machine_state = "COMM_LOST"
                        alarms_manager.trigger_alarm(
                            "PLC_COMM_LOST",
                            "CRITICAL",
                            f"Selec MiBRX-6M PLC not detected at {app_state.modbus_client.host}:{app_state.modbus_client.port}. Ethernet link down.",
                        )
                    else:
                        alarms_manager.clear_alarm("PLC_COMM_LOST")
                else:
                    alarms_manager.clear_alarm("PLC_COMM_LOST")

                payload = {
                    "type": "TELEMETRY_UPDATE",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "machine_state": app_state.current_machine_state,
                    "simulation_mode": is_sim,
                    "plc_connected": is_conn,
                    "plc_host": app_state.modbus_client.host,
                    "plc_port": app_state.modbus_client.port,
                    "signals": app_state.signals_snapshot,
                    "cycles": app_state.cycles_telemetry,
                    "latency": latency_subsystem.get_all_group_stats() if (is_sim or is_conn) else {
                        "groups": {
                            "fast_group": {"count": 0, "rtt_mean_ms": 0.0, "rtt_p50_ms": 0.0, "rtt_p95_ms": 0.0, "rtt_p99_ms": 0.0, "rtt_min_ms": 0.0, "rtt_max_ms": 0.0, "ingest_mean_ms": 0.0, "ingest_p95_ms": 0.0, "publish_mean_ms": 0.0, "update_interval_mean_ms": 0.0, "jitter_ms": 0.0},
                            "medium_group": {"count": 0, "rtt_mean_ms": 0.0, "rtt_p50_ms": 0.0, "rtt_p95_ms": 0.0, "rtt_p99_ms": 0.0, "rtt_min_ms": 0.0, "rtt_max_ms": 0.0, "ingest_mean_ms": 0.0, "ingest_p95_ms": 0.0, "publish_mean_ms": 0.0, "update_interval_mean_ms": 0.0, "jitter_ms": 0.0},
                            "slow_group": {"count": 0, "rtt_mean_ms": 0.0, "rtt_p50_ms": 0.0, "rtt_p95_ms": 0.0, "rtt_p99_ms": 0.0, "rtt_min_ms": 0.0, "rtt_max_ms": 0.0, "ingest_mean_ms": 0.0, "ingest_p95_ms": 0.0, "publish_mean_ms": 0.0, "update_interval_mean_ms": 0.0, "jitter_ms": 0.0},
                        },
                        "benchmark": {"active": False, "samples_collected": 0, "duration_seconds": 60, "elapsed_seconds": 0}
                    },
                    "alarms": alarms_manager.get_active_list(),
                    "vibration": vibration_engine.get_latest_payload(),
                    "telemetry": machine_state_manager.get_system_telemetry(),
                    "diagnostics": app_state.modbus_client.diagnostics.get_summary(),
                }
                await ws_manager.broadcast(payload)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Broadcast loop error: {e}")


async def physics_loop():
    """Background physics update loop for in-process mock PLC."""
    last = time.perf_counter()
    while True:
        try:
            await asyncio.sleep(0.05)
            now = time.perf_counter()
            dt = now - last
            last = now
            global_mock_plc.update_physics(dt)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Physics loop error: {e}")


def start_physics_task():
    """Ensure simulation physics worker is active."""
    if not app_state.physics_task or app_state.physics_task.done():
        app_state.physics_task = asyncio.create_task(physics_loop())
        logger.info("Simulation physics worker started.")


def stop_physics_task():
    """Cancel simulation physics worker."""
    if app_state.physics_task and not app_state.physics_task.done():
        app_state.physics_task.cancel()
        app_state.physics_task = None
        logger.info("Simulation physics worker stopped.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and graceful shutdown."""
    logger.info("Initializing Selec MiBRX-6M Industrial IoT Gateway backend...")
    await init_db()
    await db_buffer.start()

    # Start simulation physics if in simulation mode
    if settings.SIMULATION_MODE:
        app_state.physics_task = asyncio.create_task(physics_loop())
        logger.info("Simulation physics engine started.")

    # Start vibration acquisition engine
    await vibration_engine.start()

    # Register measurement callback and start Modbus polling
    app_state.modbus_client.set_measurement_callback(on_modbus_measurements)
    await app_state.modbus_client.start_polling()

    # Start WebSocket broadcaster
    app_state.broadcast_task = asyncio.create_task(websocket_broadcast_loop())

    yield

    # Graceful shutdown
    logger.info("Shutting down Industrial IoT Gateway...")
    if app_state.broadcast_task:
        app_state.broadcast_task.cancel()
    if app_state.physics_task:
        app_state.physics_task.cancel()
    await app_state.modbus_client.disconnect()
    await vibration_engine.stop()
    await db_buffer.stop()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Selec MiBRX-6M Industrial IoT Gateway",
    version="1.0.0",
    description="Real-time Modbus TCP monitoring, latency measurement, and safe machine control.",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Routers
app.include_router(signals_router)
app.include_router(latency_router)
app.include_router(alarms_router)
app.include_router(control_router)
app.include_router(vibration_router)
app.include_router(production_router)
app.include_router(system_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time telemetry streaming and client render timing.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Receive client messages (e.g. render timing acknowledgements, ping)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "RENDER_ACK":
                    # Client reports its local DOM render latency
                    t_publish_mono = msg.get("t_publish_mono")
                    client_render_delay_ms = msg.get("render_duration_ms")
                    client_id = msg.get("client_id", "default")
                    if client_render_delay_ms is not None:
                        ws_manager.client_rtt_estimates[client_id] = float(client_render_delay_ms)
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)


# Mount Static Frontend Files if built
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
