"""
Asynchronous Modbus TCP Polling Client with Adaptive Reconnect,
Grouped Block Reads, and Precise Latency Timestamping.
"""
import asyncio
from datetime import datetime, timezone
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

        connected = await self.connect()
        return connected

    def set_measurement_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback invoked whenever new measurements are ingested."""
        self._on_measurement_callback = callback

    async def connect(self) -> bool:
        """Establish or verify Modbus TCP connection."""
        if self.simulation_mode:
            # Check if standalone Modbus server is reachable; if not, use in-process simulation directly
            try:
                self.client = AsyncModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
                connected = await self.client.connect()
                if connected:
                    self.diagnostics.connected = True
                    logger.info(f"Connected to simulated Modbus TCP server at {self.host}:{self.port}")
                    return True
            except Exception as e:
                logger.debug(f"Direct TCP socket to {self.host}:{self.port} not open: using in-process mock PLC: {e}")
            self.diagnostics.connected = True
            logger.info("Using high-fidelity in-process Selec PLC simulation engine.")
            return True

        # Physical hardware connection
        try:
            if not self.client:
                self.client = AsyncModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
            # Use asyncio.wait_for with a short timeout so startup never hangs if PLC is offline/unreachable
            connected = await asyncio.wait_for(self.client.connect(), timeout=min(2.0, self.timeout))
            self.diagnostics.connected = bool(connected)
            if connected:
                logger.info(f"Connected to physical Selec MiBRX-6M PLC at {self.host}:{self.port}")
            else:
                logger.warning(f"Failed to connect to PLC at {self.host}:{self.port}. Polling loop will retry.")
            return bool(connected)
        except asyncio.TimeoutError:
            self.diagnostics.connected = False
            logger.warning(f"Connection timed out to PLC at {self.host}:{self.port}. Background polling will keep retrying.")
            return False
        except Exception as e:
            self.diagnostics.connected = False
            logger.warning(f"Socket connection error to PLC {self.host}:{self.port}: {e}. Background polling will keep retrying.")
            return False

    async def disconnect(self):
        """Close client connection."""
        self._running = False
        for t in self._polling_tasks:
            t.cancel()
        if self.client:
            self.client.close()
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
        all_ok = True

        # 1. Read Discrete Inputs (for fast_group)
        if group_name == "fast_group":
            discrete_sigs = [s for s in self.config.discrete_signals if s.group == group_name]
            if discrete_sigs:
                min_addr = min(s.address for s in discrete_sigs)
                max_addr = max(s.address for s in discrete_sigs)
                count = (max_addr - min_addr) + 1
                try:
                    bits = await self._read_discrete_inputs(min_addr, count)
                    t_response_mono = time.perf_counter()
                    t_response_utc = datetime.now(timezone.utc).isoformat()
                    rtt_ms = (t_response_mono - t_request_mono) * 1000.0

                    for sig in discrete_sigs:
                        idx = sig.address - min_addr
                        val = bits[idx] if idx < len(bits) else False
                        measurements[sig.name] = {
                            "name": sig.name,
                            "raw_value": 1 if val else 0,
                            "value": 1 if val else 0,
                            "unit": "",
                            "quality": "VALID" if not self.simulation_mode else "SIMULATED",
                            "group": group_name,
                            "t_request": t_request_utc,
                            "t_response": t_response_utc,
                            "t_request_mono": t_request_mono,
                            "t_response_mono": t_response_mono,
                            "rtt_ms": rtt_ms,
                        }
                except Exception as e:
                    logger.debug(f"Discrete input read failed for {group_name}: {e}")
                    all_ok = False

        # 2. Read Numerical Holding Registers in contiguous blocks
        blocks = self.group_blocks.get(group_name, [])
        for block in blocks:
            start_addr = block["start_address"]
            count = block["count"]
            t_req_mono = time.perf_counter()
            t_req_utc = datetime.now(timezone.utc).isoformat()

            try:
                registers = await self._read_holding_registers(start_addr, count)
                t_resp_mono = time.perf_counter()
                t_resp_utc = datetime.now(timezone.utc).isoformat()
                rtt_ms = (t_resp_mono - t_req_mono) * 1000.0

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
                logger.debug(f"Holding register read failed for block starting {start_addr}: {e}")
                all_ok = False

        # Record diagnostics
        t_finish_mono = time.perf_counter()
        total_rtt_ms = (t_finish_mono - t_request_mono) * 1000.0

        if all_ok and measurements:
            self.diagnostics.last_global_success_monotonic = t_finish_mono
            grp_diag = self.diagnostics.groups.get(group_name)
            if grp_diag:
                grp_diag.record_success(total_rtt_ms, t_finish_mono, datetime.now(timezone.utc).isoformat())

            # Dispatch to callback
            if self._on_measurement_callback:
                self._on_measurement_callback(measurements)
            return True
        else:
            grp_diag = self.diagnostics.groups.get(group_name)
            if grp_diag:
                grp_diag.record_failure("Read error or timeout", t_finish_mono)
            return False

    async def _read_discrete_inputs(self, address: int, count: int) -> List[bool]:
        """Low-level read discrete inputs FC 02."""
        if self.client and self.client.connected:
            resp = await self.client.read_discrete_inputs(address=address, count=count, slave=self.unit_id)
            if resp.isError():
                raise ModbusException(f"Modbus error reading discrete inputs: {resp}")
            return resp.bits[:count]
        # In-process simulation fallback
        return [global_mock_plc.read_discrete_input(address + i) for i in range(count)]

    async def _read_holding_registers(self, address: int, count: int) -> List[int]:
        """Low-level read holding registers FC 03."""
        if self.client and self.client.connected:
            resp = await self.client.read_holding_registers(address=address, count=count, slave=self.unit_id)
            if resp.isError():
                raise ModbusException(f"Modbus error reading holding registers: {resp}")
            return resp.registers[:count]

        # In-process simulation fallback: decode simulated state into raw 16-bit register words
        return self._simulate_holding_registers(address, count)

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
                resp = await self.client.write_coil(address=address, value=value, slave=self.unit_id)
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
                resp = await self.client.write_register(address=address, value=encoded, slave=self.unit_id)
                if resp.isError():
                    return False, f"Modbus write register error: {resp}"
            else:
                global_mock_plc.write_holding_register(address, value)
            return True, f"Successfully wrote register {address} -> {value}"
        except Exception as e:
            return False, f"Exception writing register {address}: {e}"
