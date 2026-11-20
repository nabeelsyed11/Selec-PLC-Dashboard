"""
Asynchronous Modbus TCP Polling Client with Adaptive Reconnect,
Grouped Block Reads, and Precise Latency Timestamping.
"""
import asyncio
from datetime import datetime, timezone
import inspect
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Callable

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from app.core.config import settings
from app.plc.decoder import decode_signal, encode_16bit_uint
from app.plc.diagnostics import CommunicationDiagnosticsManager
from app.plc.register_map import RegisterMapConfig, group_contiguous_registers
from app.simulation.mock_plc import global_mock_plc

logger = logging.getLogger("plc.modbus_client")


def call_modbus(method, *args, unit_id: int = 1, **kwargs):
    """
    Invoke a PyModbus client method with version-agnostic unit/slave parameter.
    PyModbus <3.0 used `unit`.
    PyModbus 3.0-3.7 used `slave`.
    PyModbus 3.8+ uses `device_id`.
    """
    try:
        params = inspect.signature(method).parameters
        if "device_id" in params:
            kwargs["device_id"] = unit_id
        elif "slave" in params:
            kwargs["slave"] = unit_id
        elif "unit" in params:
            kwargs["unit"] = unit_id
        else:
            kwargs["device_id"] = unit_id
    except Exception:
        kwargs["device_id"] = unit_id
    return method(*args, **kwargs)


class SelecModbusClient:
    """
    Manages connection, grouped polling, decoding, and writing
    for the Selec MiBRX-6M PLC.
    """

    def __init__(self, config: RegisterMapConfig):
        self.config = config
        self.host = settings.PLC_HOST
        self.port = settings.PLC_PORT
        self.unit_id = settings.PLC_UNIT_ID
        self.timeout = settings.PLC_TIMEOUT_SECONDS
        self.simulation_mode = settings.SIMULATION_MODE

        self.client: Optional[AsyncModbusTcpClient] = None
        self.diagnostics = CommunicationDiagnosticsManager(
            max_data_age_seconds=config.plc_connection.get("max_data_age_seconds", 3.0)
        )

        # Initialize diagnostic groups
        for grp_name, grp_cfg in config.polling_groups.items():
            self.diagnostics.register_group(grp_name, grp_cfg.interval_ms)

        # Precompute contiguous read blocks for each polling group
        self.group_blocks: Dict[str, List[Dict[str, Any]]] = {}
        for grp_name in config.polling_groups.keys():
            signals = [s for s in config.numerical_signals if s.group == grp_name]
            self.group_blocks[grp_name] = group_contiguous_registers(signals)

        self._polling_tasks: List[asyncio.Task] = []
        self._running = False
        self._on_measurement_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._reconnect_lock: Optional[asyncio.Lock] = None
        self._io_lock: Optional[asyncio.Lock] = None
        self._last_reconnect_time = 0.0

    @property
    def io_lock(self) -> asyncio.Lock:
        if self._io_lock is None:
            self._io_lock = asyncio.Lock()
        return self._io_lock

    async def reconfigure(
        self,
        host: str,
        port: int,
        unit_id: int,
        simulation_mode: bool,
        timeout: float = 1.5,
    ) -> bool:
        """Dynamically update connection parameters and reconnect on the fly."""
        logger.info(f"Reconfiguring Modbus client to {host}:{port} (Unit {unit_id}, Sim: {simulation_mode})")
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.simulation_mode = simulation_mode
        self.timeout = timeout
        self.diagnostics.connected = False

        if not simulation_mode:
            global_mock_plc.reset()
            if self._on_measurement_callback:
                disconnected_meas: Dict[str, Any] = {}
                now_iso = datetime.now(timezone.utc).isoformat()
                now_mono = time.perf_counter()
                for sig in self.config.discrete_signals:
                    disconnected_meas[sig.name] = {
                        "name": sig.name,
                        "raw_value": 0,
                        "value": 0,
                        "unit": "",
                        "quality": "DISCONNECTED",
                        "group": sig.group,
                        "t_request": now_iso,
                        "t_response": None,
                        "t_request_mono": now_mono,
                        "t_response_mono": now_mono,
                        "rtt_ms": 0.0,
                    }
                for sig in self.config.numerical_signals:
                    disconnected_meas[sig.name] = {
                        "name": sig.name,
                        "raw_value": 0,
                        "value": 0.0,
                        "unit": sig.engineering_unit,
                        "quality": "DISCONNECTED",
                        "group": sig.group,
                        "t_request": now_iso,
                        "t_response": None,
                        "t_request_mono": now_mono,
                        "t_response_mono": now_mono,
                        "rtt_ms": 0.0,
                    }
                self._on_measurement_callback(disconnected_meas)

        self._last_reconnect_time = 0.0
        connected = await self.connect(force=True)
        return connected

    def set_measurement_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback invoked whenever new measurements are ingested."""
        self._on_measurement_callback = callback

    async def connect(self, force: bool = False) -> bool:
        """Establish or verify Modbus TCP connection."""
        if self.simulation_mode:
            # Check if standalone Modbus server is running on localhost; otherwise use in-process engine
            if self.host in ("127.0.0.1", "localhost"):
                try:
                    client = AsyncModbusTcpClient(self.host, port=self.port, timeout=0.1)
                    connected = await asyncio.wait_for(client.connect(), timeout=0.15)
                    if connected:
                        self.client = client
                        self.diagnostics.connected = True
                        logger.info(f"Connected to simulated Modbus TCP server at {self.host}:{self.port}")
                        return True
                    else:
                        client.close()
                except Exception:
                    pass
            self.diagnostics.connected = True
            logger.info("Using high-fidelity in-process Selec PLC simulation engine.")
            return True

        # Physical hardware connection - If already connected, do not tear down healthy socket
        if self.client and getattr(self.client, "connected", False) and not force:
            self.diagnostics.connected = True
            return True

        # Throttle reconnection attempts to at most once every 1.0s unless forced
        now = time.monotonic()
        if not force and now - self._last_reconnect_time < 1.0:
            return self.diagnostics.connected

        if self._reconnect_lock is None:
            self._reconnect_lock = asyncio.Lock()

        if self._reconnect_lock.locked() and not force:
            return self.diagnostics.connected

        async with self._reconnect_lock:
            now = time.monotonic()
            if not force and now - self._last_reconnect_time < 1.0:
                return self.diagnostics.connected
            self._last_reconnect_time = now

            try:
                if self.client:
                    try:
                        self.client.close()
                    except Exception:
                        pass
                logger.info(f"Opening Modbus TCP socket to Selec PLC at {self.host}:{self.port}...")
                self.client = AsyncModbusTcpClient(self.host, port=self.port, timeout=max(2.5, self.timeout))
                connected = await asyncio.wait_for(self.client.connect(), timeout=max(2.5, self.timeout))
                self.diagnostics.connected = bool(connected)
                if connected:
                    logger.info(f"✓ CONNECTED to physical Selec MiBRX-6M PLC at {self.host}:{self.port}")
                else:
                    logger.warning(f"✗ Failed to connect to PLC at {self.host}:{self.port}. Retrying in background...")
                return bool(connected)
            except (asyncio.TimeoutError, Exception) as e:
                self.diagnostics.connected = False
                logger.warning(f"✗ Connection attempt to PLC at {self.host}:{self.port} failed: {e}")
                return False

    async def disconnect(self):
        """Close client connection and cleanly stop polling tasks."""
        self._running = False
        for t in self._polling_tasks:
            if not t.done():
                t.cancel()
        if self._polling_tasks:
            await asyncio.gather(*self._polling_tasks, return_exceptions=True)
            self._polling_tasks.clear()
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
        self.diagnostics.connected = False

    async def start_polling(self):
        """Start independent polling loops for each configured group."""
        self._running = True
        try:
            await self.connect()
        except Exception as e:
            logger.warning(f"Initial PLC connection failed: {e}. Worker loops will retry in background.")

        for grp_name, grp_cfg in self.config.polling_groups.items():
            if grp_cfg.enabled:
                task = asyncio.create_task(self._poll_loop(grp_name, grp_cfg.interval_ms))
                self._polling_tasks.append(task)
        logger.info(f"Started {len(self._polling_tasks)} Modbus polling worker tasks.")

    async def _poll_loop(self, group_name: str, interval_ms: int):
        """Dedicated polling worker for a specific signal group."""
        interval_sec = interval_ms / 1000.0
        backoff_ms = self.config.plc_connection.get("backoff_initial_ms", 100)
        max_backoff_ms = self.config.plc_connection.get("backoff_max_ms", 3000)

        while self._running:
            start_loop_mono = time.perf_counter()
            success = await self._poll_group(group_name)

            if success:
                backoff_ms = self.config.plc_connection.get("backoff_initial_ms", 100)
                elapsed = time.perf_counter() - start_loop_mono
                sleep_sec = max(0.01, interval_sec - elapsed)
                await asyncio.sleep(sleep_sec)
            else:
                # Exponential backoff on communication failure
                backoff_sec = backoff_ms / 1000.0
                logger.debug(f"Group {group_name} poll failed. Backoff sleep {backoff_sec:.2f}s")
                await asyncio.sleep(backoff_sec)
                backoff_ms = min(max_backoff_ms, backoff_ms * 2)
                # Attempt reconnect
                await self.connect()

    async def _poll_group(self, group_name: str) -> bool:
        """Execute a single poll cycle for all signals in group."""
        t_request_mono = time.perf_counter()
        t_request_utc = datetime.now(timezone.utc).isoformat()
        measurements: Dict[str, Any] = {}
        successful_reads = 0

        # 1. Read Discrete Inputs & Coils (for fast_group)
        if group_name == "fast_group":
            discrete_sigs = [s for s in self.config.discrete_signals if s.group == group_name]
            if discrete_sigs:
                chunks = self._group_discrete_signals(discrete_sigs)
                for chunk in chunks:
                    sig_type = chunk["type"]
                    min_addr = chunk["start_address"]
                    count = chunk["count"]
                    chunk_sigs = chunk["signals"]
                    t_chunk_mono = time.perf_counter()
                    t_chunk_utc = datetime.now(timezone.utc).isoformat()
                    try:
                        if sig_type == "coil":
                            bits = await self._read_coils(min_addr, count)
                        else:
                            bits = await self._read_discrete_inputs(min_addr, count)
                        t_response_mono = time.perf_counter()
                        t_response_utc = datetime.now(timezone.utc).isoformat()
                        rtt_ms = (t_response_mono - t_chunk_mono) * 1000.0
                        successful_reads += 1

                        for sig in chunk_sigs:
                            idx = sig.address - min_addr
                            val = bits[idx] if idx < len(bits) else False
                            measurements[sig.name] = {
                                "name": sig.name,
                                "raw_value": 1 if val else 0,
                                "value": 1 if val else 0,
                                "unit": "",
                                "quality": "VALID" if not self.simulation_mode else "SIMULATED",
                                "group": group_name,
                                "t_request": t_chunk_utc,
                                "t_response": t_response_utc,
                                "t_request_mono": t_chunk_mono,
                                "t_response_mono": t_response_mono,
                                "rtt_ms": rtt_ms,
                            }
                    except Exception as e:
                        logger.debug(f"{sig_type} read failed for block starting {min_addr}: {e}")
                        for sig in chunk_sigs:
                            measurements[sig.name] = {
                                "name": sig.name,
                                "raw_value": 0,
                                "value": 0,
                                "unit": "",
                                "quality": "DISCONNECTED" if not self.simulation_mode else "SIMULATED",
                                "group": group_name,
                                "t_request": t_chunk_utc,
                                "t_response": None,
                                "t_request_mono": t_chunk_mono,
                                "t_response_mono": t_chunk_mono,
                                "rtt_ms": 0.0,
                            }

        # 2. Read Numerical Holding Registers in contiguous blocks
        blocks = self.group_blocks.get(group_name, [])
        for block in blocks:
            start_addr = block["start_address"]
            count = block["count"]
            fc = block.get("function_code", 3)
            t_req_mono = time.perf_counter()
            t_req_utc = datetime.now(timezone.utc).isoformat()

            try:
                registers = await self._read_registers(start_addr, count, function_code=fc)
                t_resp_mono = time.perf_counter()
                t_resp_utc = datetime.now(timezone.utc).isoformat()
                rtt_ms = (t_resp_mono - t_req_mono) * 1000.0
                successful_reads += 1

                for sig in block["signals"]:
                    rel_idx = sig.address - start_addr
                    scaled_val = decode_signal(
                        registers=registers,
                        data_type=sig.data_type,
                        index=rel_idx,
                        byte_order=sig.byte_order,
                        word_swap=sig.word_swap,
                        scaling_factor=sig.scaling_factor,
                        offset=sig.offset,
                    )
                    raw_val = registers[rel_idx] if rel_idx < len(registers) else 0

                    measurements[sig.name] = {
                        "name": sig.name,
                        "raw_value": raw_val,
                        "value": scaled_val,
                        "unit": sig.engineering_unit,
                        "quality": "VALID" if not self.simulation_mode else "SIMULATED",
                        "group": group_name,
                        "t_request": t_req_utc,
                        "t_response": t_resp_utc,
                        "t_request_mono": t_req_mono,
                        "t_response_mono": t_resp_mono,
                        "rtt_ms": rtt_ms,
                    }
            except Exception as e:
                logger.debug(f"Holding register block read failed for start {start_addr} (count {count}): {e}. Attempting individual signal fallback...")
                for sig in block["signals"]:
                    t_sig_mono = time.perf_counter()
                    t_sig_utc = datetime.now(timezone.utc).isoformat()
                    try:
                        sig_regs = await self._read_registers(sig.address, sig.register_count, function_code=sig.function_code)
                        t_sig_resp_mono = time.perf_counter()
                        t_sig_resp_utc = datetime.now(timezone.utc).isoformat()
                        rtt_sig = (t_sig_resp_mono - t_sig_mono) * 1000.0
                        successful_reads += 1
                        scaled_val = decode_signal(
                            registers=sig_regs,
                            data_type=sig.data_type,
                            index=0,
                            byte_order=sig.byte_order,
                            word_swap=sig.word_swap,
                            scaling_factor=sig.scaling_factor,
                            offset=sig.offset,
                        )
                        raw_val = sig_regs[0] if sig_regs else 0
                        measurements[sig.name] = {
                            "name": sig.name,
                            "raw_value": raw_val,
                            "value": scaled_val,
                            "unit": sig.engineering_unit,
                            "quality": "VALID" if not self.simulation_mode else "SIMULATED",
                            "group": group_name,
                            "t_request": t_sig_utc,
                            "t_response": t_sig_resp_utc,
                            "t_request_mono": t_sig_mono,
                            "t_response_mono": t_sig_resp_mono,
                            "rtt_ms": rtt_sig,
                        }
                    except Exception as sig_err:
                        logger.debug(f"Individual read failed for {sig.name} at {sig.address}: {sig_err}")
                        measurements[sig.name] = {
                            "name": sig.name,
                            "raw_value": 0,
                            "value": 0.0,
                            "unit": sig.engineering_unit,
                            "quality": "DISCONNECTED" if not self.simulation_mode else "SIMULATED",
                            "group": group_name,
                            "t_request": t_sig_utc,
                            "t_response": None,
                            "t_request_mono": t_sig_mono,
                            "t_response_mono": t_sig_mono,
                            "rtt_ms": 0.0,
                        }

        # Record diagnostics
        t_finish_mono = time.perf_counter()
        total_rtt_ms = (t_finish_mono - t_request_mono) * 1000.0

        # Connection is healthy if at least one block read succeeded or TCP client is connected
        if successful_reads > 0:
            self.diagnostics.connected = True
            self.diagnostics.last_global_success_monotonic = t_finish_mono
            grp_diag = self.diagnostics.groups.get(group_name)
            if grp_diag:
                grp_diag.record_success(total_rtt_ms, t_finish_mono, datetime.now(timezone.utc).isoformat())

            # Dispatch to callback
            if self._on_measurement_callback:
                self._on_measurement_callback(measurements)
            return True
        else:
            if not self.simulation_mode:
                is_stale = self.diagnostics.is_data_stale(self.diagnostics.last_global_success_monotonic)
                if is_stale or not (self.client and getattr(self.client, "connected", False)):
                    self.diagnostics.connected = False
            grp_diag = self.diagnostics.groups.get(group_name)
            if grp_diag:
                grp_diag.record_failure("Read error or timeout", t_finish_mono)

            # When physical PLC is disconnected, report true DISCONNECTED state (no fake/stale values)
            if not self.simulation_mode and self._on_measurement_callback:
                self._on_measurement_callback(measurements)
            return False

    def _group_discrete_signals(self, signals: List[Any]) -> List[Dict[str, Any]]:
        """Groups discrete signals by type (coil vs discrete_input) and contiguous address ranges."""
        if not signals:
            return []
        sorted_sigs = sorted(signals, key=lambda s: (s.type, s.address))
        chunks: List[Dict[str, Any]] = []
        current = {
            "type": sorted_sigs[0].type,
            "start_address": sorted_sigs[0].address,
            "count": 1,
            "signals": [sorted_sigs[0]],
        }
        for s in sorted_sigs[1:]:
            curr_end = current["start_address"] + current["count"]
            if s.type == current["type"] and (s.address - curr_end) <= 2:
                current["count"] = (s.address + 1) - current["start_address"]
                current["signals"].append(s)
            else:
                chunks.append(current)
                current = {
                    "type": s.type,
                    "start_address": s.address,
                    "count": 1,
                    "signals": [s],
                }
        chunks.append(current)
        return chunks

    async def _read_coils(self, address: int, count: int) -> List[bool]:
        """Low-level read coils FC 01 with fallback to Read Discrete Inputs FC 02."""
        if not self.simulation_mode and not (self.client and getattr(self.client, "connected", False)):
            await self.connect()

        if self.client and getattr(self.client, "connected", False):
            async with self.io_lock:
                resp = await call_modbus(self.client.read_coils, address=address, count=count, unit_id=self.unit_id)
                if resp.isError() or not hasattr(resp, "bits"):
                    # Attempt address - 1 (1-based to 0-based offset tolerance)
                    try:
                        resp_adj = await call_modbus(self.client.read_coils, address=max(0, address - 1), count=count, unit_id=self.unit_id)
                        if not resp_adj.isError() and hasattr(resp_adj, "bits"):
                            return resp_adj.bits[:count]
                    except Exception:
                        pass
                    # Attempt address + 1
                    try:
                        resp_adj2 = await call_modbus(self.client.read_coils, address=address + 1, count=count, unit_id=self.unit_id)
                        if not resp_adj2.isError() and hasattr(resp_adj2, "bits"):
                            return resp_adj2.bits[:count]
                    except Exception:
                        pass
                    # Attempt fallback to Discrete Inputs FC 02
                    try:
                        resp_di = await call_modbus(self.client.read_discrete_inputs, address=address, count=count, unit_id=self.unit_id)
                        if not resp_di.isError() and hasattr(resp_di, "bits"):
                            return resp_di.bits[:count]
                    except Exception:
                        pass
                    raise ModbusException(f"Modbus error reading coils at {address}: {resp}")
                return resp.bits[:count]

        if self.simulation_mode:
            return [global_mock_plc.read_coils(address + i) for i in range(count)]

        raise ModbusException(f"PLC not connected at {self.host}:{self.port}")

    async def _read_discrete_inputs(self, address: int, count: int) -> List[bool]:
        """Low-level read discrete inputs FC 02 with fallback to Read Coils FC 01."""
        if not self.simulation_mode and not (self.client and getattr(self.client, "connected", False)):
            await self.connect()

        if self.client and getattr(self.client, "connected", False):
            async with self.io_lock:
                resp = await call_modbus(self.client.read_discrete_inputs, address=address, count=count, unit_id=self.unit_id)
                if resp.isError():
                    # Attempt fallback to Read Coils (FC 01) - common on Selec PLCs
                    try:
                        resp_coils = await call_modbus(self.client.read_coils, address=address, count=count, unit_id=self.unit_id)
                        if not resp_coils.isError() and hasattr(resp_coils, "bits"):
                            return resp_coils.bits[:count]
                    except Exception:
                        pass
                    raise ModbusException(f"Modbus error reading discrete inputs: {resp}")
                return resp.bits[:count]

        # ONLY simulate if explicitly in simulation mode!
        if self.simulation_mode:
            return [global_mock_plc.read_discrete_input(address + i) for i in range(count)]
        
        raise ModbusException(f"PLC not connected at {self.host}:{self.port}")

    async def _read_registers(self, address: int, count: int, function_code: int = 3) -> List[int]:
        """Low-level register reader supporting FC 03 (Holding) and FC 04 (Input) with mutual fallback."""
        if not self.simulation_mode and not (self.client and getattr(self.client, "connected", False)):
            await self.connect()

        if self.client and getattr(self.client, "connected", False):
            async with self.io_lock:
                primary_fn = self.client.read_input_registers if function_code == 4 else self.client.read_holding_registers
                secondary_fn = self.client.read_holding_registers if function_code == 4 else self.client.read_input_registers

                resp = await call_modbus(primary_fn, address=address, count=count, unit_id=self.unit_id)
                if resp.isError() or not hasattr(resp, "registers"):
                    # Fallback 1: try secondary function code at same address
                    try:
                        resp_sec = await call_modbus(secondary_fn, address=address, count=count, unit_id=self.unit_id)
                        if not resp_sec.isError() and hasattr(resp_sec, "registers"):
                            return resp_sec.registers[:count]
                    except Exception:
                        pass
                    # Fallback 2: try 1-based offset tolerance (address - 1)
                    for fn in (primary_fn, secondary_fn):
                        try:
                            resp_adj = await call_modbus(fn, address=max(0, address - 1), count=count, unit_id=self.unit_id)
                            if not resp_adj.isError() and hasattr(resp_adj, "registers"):
                                return resp_adj.registers[:count]
                        except Exception:
                            pass
                    # Fallback 3: try 0-based offset tolerance (address + 1)
                    for fn in (primary_fn, secondary_fn):
                        try:
                            resp_adj2 = await call_modbus(fn, address=address + 1, count=count, unit_id=self.unit_id)
                            if not resp_adj2.isError() and hasattr(resp_adj2, "registers"):
                                return resp_adj2.registers[:count]
                        except Exception:
                            pass
                    raise ModbusException(f"Modbus error reading registers at {address}: {resp}")
                return resp.registers[:count]

        if self.simulation_mode:
            return self._simulate_holding_registers(address, count)

        raise ModbusException(f"PLC not connected at {self.host}:{self.port}")

    async def _read_holding_registers(self, address: int, count: int) -> List[int]:
        """Legacy alias pointing to _read_registers."""
        return await self._read_registers(address, count, function_code=3)

    def _simulate_holding_registers(self, address: int, count: int) -> List[int]:
        """Maps global_mock_plc physical state to raw 16-bit Modbus registers."""
        state = global_mock_plc
        regs: Dict[int, int] = {}

        # 0: Load cell raw (0.1 kg scaling -> weight * 10)
        regs[0] = int(max(0.0, state.load_cell_current_kg * 10.0)) & 0xFFFF
        # 1: Motor temp (0.1 °C scaling -> temp * 10)
        regs[1] = int(state.motor_temp_c * 10.0) & 0xFFFF
        # 2-3: Encoder count 32-bit UINT (Hi word at 2, Lo word at 3)
        enc = state.encoder_count
        regs[2] = (enc >> 16) & 0xFFFF
        regs[3] = enc & 0xFFFF
        # 4: Belt speed (0.01 m/s scaling -> speed * 100)
        regs[4] = int(state.conveyor_speed_mps * 100.0) & 0xFFFF
        # 5-6: Production total 32-bit UINT
        prod = state.production_total
        regs[5] = (prod >> 16) & 0xFFFF
        regs[6] = prod & 0xFFFF
        # 7: Production rate ppm (0.1 ppm scaling)
        regs[7] = int(state.production_rate_ppm * 10.0) & 0xFFFF

        # Energy Meter Floats (IEEE-754 across 2 registers)
        import struct
        def float_to_regs(f_val: float) -> Tuple[int, int]:
            packed = struct.pack(">f", float(f_val))
            return struct.unpack(">HH", packed)

        regs[10], regs[11] = float_to_regs(state.mains_voltage_v)
        regs[12], regs[13] = float_to_regs(state.mains_current_a)
        regs[14], regs[15] = float_to_regs(state.active_power_kw)
        regs[16], regs[17] = float_to_regs(state.power_factor)
        regs[18] = int(state.grid_frequency_hz * 100.0) & 0xFFFF
        regs[20], regs[21] = float_to_regs(state.cumulative_kwh)

        # SCADA QW0 / QW3 / Electrical registers (simulated for both 0-based & 1-based)
        regs[767] = 7500 # QW0 (1-based: 30768 -> 767)
        regs[768] = 7500 # QW0 (0-based: 30768 -> 768)
        regs[770] = int(state.vfd_current_speed_hz) & 0xFFFF  # QW3 (1-based: 30771 -> 770)
        regs[771] = int(state.vfd_current_speed_hz) & 0xFFFF  # QW3 (0-based: 30771 -> 771)
        # Word-swapped float helper (CDAB)
        def float_to_regs_swapped(f_val: float) -> Tuple[int, int]:
            r_hi, r_lo = float_to_regs(f_val)
            return r_lo, r_hi

        regs[1541], regs[1542] = float_to_regs_swapped(state.mains_voltage_v)
        regs[1542], regs[1543] = float_to_regs_swapped(state.mains_voltage_v)      # %ID3 Voltage (float32)
        regs[1544], regs[1545] = float_to_regs_swapped(state.mains_current_a)      # ID4 Current (float32)
        regs[1546], regs[1547] = float_to_regs_swapped(state.power_factor)         # ID5 Power Factor (float32)

        # VFD feedback
        regs[25] = int(state.vfd_current_speed_hz * 10.0) & 0xFFFF
        regs[26] = int(state.vfd_motor_current_a * 10.0) & 0xFFFF
        regs[29] = state.plc_cycle_counter & 0xFFFF
        regs[30] = int(state.vfd_speed_sp_hz * 10.0) & 0xFFFF

        result = []
        for a in range(address, address + count):
            result.append(regs.get(a, 0))
        return result

    async def write_coil(self, address: int, value: bool) -> Tuple[bool, str]:
        """
        Write Single Coil FC 05 with allowlist enforcement.
        Returns (success: bool, message: str).
        """
        # Safety check: Validate address is on allowlist
        entry = next((e for e in self.config.writable_allowlist if e.address == address and e.function_code == 5), None)
        if not entry:
            return False, f"SECURITY VIOLATION: Address {address} (FC 05) is not in the writable allowlist!"

        try:
            if self.client and self.client.connected:
                resp = await call_modbus(self.client.write_coil, address=address, value=value, unit_id=self.unit_id)
                if resp.isError():
                    return False, f"Modbus write coil error: {resp}"
            else:
                global_mock_plc.write_coil(address, value)
            return True, f"Successfully wrote coil {address} -> {value}"
        except Exception as e:
            return False, f"Exception writing coil {address}: {e}"

    async def write_register(self, address: int, value: int) -> Tuple[bool, str]:
        """
        Write Single Holding Register FC 06 with allowlist enforcement.
        Returns (success: bool, message: str).
        """
        entry = next((e for e in self.config.writable_allowlist if e.address == address and e.function_code == 6), None)
        if not entry:
            return False, f"SECURITY VIOLATION: Address {address} (FC 06) is not in the writable allowlist!"

        if entry.min_value is not None and value < entry.min_value:
            return False, f"Value {value} below minimum permitted limit ({entry.min_value})"
        if entry.max_value is not None and value > entry.max_value:
            return False, f"Value {value} exceeds maximum permitted limit ({entry.max_value})"

        try:
            if self.client and self.client.connected:
                encoded = encode_16bit_uint(value)
                resp = await call_modbus(self.client.write_register, address=address, value=encoded, unit_id=self.unit_id)
                if resp.isError():
                    return False, f"Modbus write register error: {resp}"
            else:
                global_mock_plc.write_holding_register(address, value)
            return True, f"Successfully wrote register {address} -> {value}"
        except Exception as e:
            return False, f"Exception writing register {address}: {e}"
