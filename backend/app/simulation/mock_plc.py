"""
Realistic Selec MiBRX-6M PLC Simulation Engine
Simulates industrial process physics, sensor noise, conveyor mechanics,
thermal inertia, high-speed counters, and Modbus TCP server endpoints.
"""
import asyncio
import math
import random
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("simulation.mock_plc")


class MockPlcState:
    """Simulates physical states and register memory of a Selec MiBRX-6M machine."""

    def __init__(self):
        # Simulation control
        self.running: bool = True
        self.simulated_fault: Optional[str] = None
        self.artificial_delay_ms: float = 0.0

        # Physical machine variables
        self.emergency_stop_ok: bool = True
        self.safety_guard_closed: bool = True
        self.ambient_temp_c: float = 24.5

        # Conveyor & VFD
        self.vfd_run_cmd: bool = False
        self.vfd_running: bool = False
        self.vfd_fault: bool = False
        self.vfd_speed_sp_hz: float = 40.0      # Target frequency (Hz)
        self.vfd_current_speed_hz: float = 0.0  # Actual ramping frequency (Hz)
        self.vfd_motor_current_a: float = 0.0

        # Encoder & Conveyor Mechanics
        self.pulses_per_rev: int = 1024
        self.roller_diameter_m: float = 0.1
        self.roller_circ_m: float = math.pi * self.roller_diameter_m
        self.encoder_count: int = 152000
        self.conveyor_speed_mps: float = 0.0
        self.encoder_max_count: int = 4294967295  # 32-bit rollover

        # Belt Slip Detection
        self.belt_slip_active: bool = False
        self.belt_slip_timer: float = 0.0

        # Thermal Model (Motor Stator)
        self.motor_temp_c: float = 28.0
        self.thermal_tau_heat: float = 180.0    # Seconds thermal time constant heating
        self.thermal_tau_cool: float = 300.0    # Seconds thermal time constant cooling
        self.max_running_temp_c: float = 68.0

        # Load Cell
        self.load_cell_tare_kg: float = 0.0
        self.load_cell_current_kg: float = 0.0
        self.item_on_scale: bool = False
        self.item_scale_timer: float = 0.0
        self.current_item_weight_kg: float = 0.0

        # Production Counter
        self.production_total: int = 1420
        self.production_shift: int = 380
        self.production_rate_ppm: float = 0.0
        self.part_sensor_active: bool = False
        self.part_interval_sec: float = 2.5
        self.part_timer: float = 0.0

        # Pusher Actuator
        self.pusher_cmd: bool = False
        self.pusher_extended: bool = False
        self.pusher_retracted: bool = True
        self.pusher_travel_time: float = 0.35   # seconds
        self.pusher_transition_timer: float = 0.0
        self.pusher_fault_inject: bool = False  # If true, sensor fails to report extension

        # Electrical Energy Meter
        self.mains_voltage_v: float = 230.0
        self.mains_current_a: float = 0.0
        self.active_power_kw: float = 0.0
        self.power_factor: float = 0.91
        self.grid_frequency_hz: float = 50.02
        self.cumulative_kwh: float = 1845.620

        # PLC Scan Cycle Counter (Sequence)
        self.plc_cycle_counter: int = 0
        self.last_update_monotonic: float = time.perf_counter()

    def reset(self):
        """Reset mock simulation physical state back to initial."""
        self.__init__()

    def update_physics(self, dt: float):
        """Advance physical simulation by dt seconds."""
        self.plc_cycle_counter = (self.plc_cycle_counter + 1) % 65536

        # 1. VFD and Conveyor Motion
        interlocks_met = self.emergency_stop_ok and self.safety_guard_closed and not self.vfd_fault

        if self.vfd_run_cmd and interlocks_met:
            self.vfd_running = True
            # Ramp acceleration (10 Hz/s)
            if self.vfd_current_speed_hz < self.vfd_speed_sp_hz:
                self.vfd_current_speed_hz = min(
                    self.vfd_speed_sp_hz, self.vfd_current_speed_hz + 10.0 * dt
                )
            elif self.vfd_current_speed_hz > self.vfd_speed_sp_hz:
                self.vfd_current_speed_hz = max(
                    self.vfd_speed_sp_hz, self.vfd_current_speed_hz - 15.0 * dt
                )
        else:
            # Coast down (20 Hz/s)
            self.vfd_current_speed_hz = max(0.0, self.vfd_current_speed_hz - 20.0 * dt)
            if self.vfd_current_speed_hz == 0.0:
                self.vfd_running = False

        # Calculate linear belt speed (at 50 Hz, motor runs ~1450 RPM -> gearbox 15:1 -> roller ~96.6 RPM -> 0.506 m/s)
        motor_rpm = (self.vfd_current_speed_hz / 50.0) * 1440.0
        roller_rpm = motor_rpm / 12.0
        self.conveyor_speed_mps = (roller_rpm / 60.0) * self.roller_circ_m

        # 2. Encoder pulse accumulation with rollover
        pulses_per_sec = (roller_rpm / 60.0) * self.pulses_per_rev
        new_pulses = int(pulses_per_sec * dt)
        self.encoder_count = (self.encoder_count + new_pulses) % self.encoder_max_count

        # 3. Belt Slip Logic
        if self.simulated_fault == "belt_slip":
            self.belt_slip_active = True
        elif self.vfd_running and self.conveyor_speed_mps < 0.05 and self.vfd_current_speed_hz > 15.0:
            self.belt_slip_active = True
        else:
            self.belt_slip_active = False

        # 4. Thermal Model
        if self.simulated_fault == "overheat":
            target_temp = 96.0  # Critical high temperature
            rate = (target_temp - self.motor_temp_c) / 30.0
            self.motor_temp_c += rate * dt
        elif self.vfd_running:
            # Motor heats proportionally to current squared and speed
            load_factor = (self.vfd_current_speed_hz / 50.0)
            target_temp = self.ambient_temp_c + (self.max_running_temp_c - self.ambient_temp_c) * (load_factor ** 1.2)
            self.motor_temp_c += (target_temp - self.motor_temp_c) * (dt / self.thermal_tau_heat)
        else:
            # Cooling toward ambient
            self.motor_temp_c += (self.ambient_temp_c - self.motor_temp_c) * (dt / self.thermal_tau_cool)

        # 5. Production Parts & Optical Sensor
        if self.conveyor_speed_mps > 0.1:
            self.part_timer += dt
            if self.part_timer >= self.part_interval_sec:
                self.part_timer = 0.0
                self.part_sensor_active = True
                self.production_total += 1
                self.production_shift += 1
                # Trigger item on scale
                self.item_on_scale = True
                self.item_scale_timer = 0.8
                self.current_item_weight_kg = 25.0 + random.uniform(-4.5, 5.2)
            elif self.part_timer > 0.3:
                self.part_sensor_active = False
        else:
            self.part_sensor_active = False

        # Calculate production rate (ppm)
        if self.conveyor_speed_mps > 0.05:
            self.production_rate_ppm = (60.0 / self.part_interval_sec) * (self.vfd_current_speed_hz / 50.0)
        else:
            self.production_rate_ppm = 0.0

        # 6. Load Cell platform weight
        if self.item_on_scale:
            self.item_scale_timer -= dt
            if self.item_scale_timer <= 0:
                self.item_on_scale = False
                self.load_cell_current_kg = self.load_cell_tare_kg + random.uniform(-0.04, 0.04)
            else:
                self.load_cell_current_kg = self.load_cell_tare_kg + self.current_item_weight_kg + random.uniform(-0.08, 0.08)
        else:
            self.load_cell_current_kg = self.load_cell_tare_kg + random.uniform(-0.04, 0.04)

        # 7. Pusher Actuator Dynamics
        if self.pusher_cmd:
            if not self.pusher_extended:
                self.pusher_transition_timer += dt
                if self.pusher_transition_timer >= self.pusher_travel_time:
                    self.pusher_extended = True
                    self.pusher_retracted = False
            # Check for fault injection: sensor failure
            if self.pusher_fault_inject:
                self.pusher_extended_sensor = False
            else:
                self.pusher_extended_sensor = self.pusher_extended
            self.pusher_retracted_sensor = False
        else:
            if not self.pusher_retracted:
                self.pusher_transition_timer += dt
                if self.pusher_transition_timer >= self.pusher_travel_time:
                    self.pusher_retracted = True
                    self.pusher_extended = False
            self.pusher_extended_sensor = False
            self.pusher_retracted_sensor = self.pusher_retracted

        # 8. Electrical Energy Meter
        self.mains_voltage_v = 230.0 + random.uniform(-1.8, 2.2)
        self.grid_frequency_hz = 50.0 + random.uniform(-0.04, 0.04)

        if self.vfd_running:
            self.vfd_motor_current_a = 4.2 + (self.vfd_current_speed_hz / 50.0) * 12.8 + (3.0 if self.item_on_scale else 0.0)
            self.mains_current_a = self.vfd_motor_current_a * 1.05 + 1.2
            self.power_factor = 0.88 + random.uniform(-0.02, 0.02)
            # P = sqrt(3) * V * I * PF / 1000
            self.active_power_kw = (1.732 * self.mains_voltage_v * self.mains_current_a * self.power_factor) / 1000.0
            # Cumulative energy (kWh = kW * dt / 3600)
            self.cumulative_kwh += self.active_power_kw * (dt / 3600.0)
        else:
            self.vfd_motor_current_a = 0.0
            self.mains_current_a = 0.6  # Standby control electronics
            self.power_factor = 0.45
            self.active_power_kw = (1.732 * self.mains_voltage_v * self.mains_current_a * self.power_factor) / 1000.0
            self.cumulative_kwh += self.active_power_kw * (dt / 3600.0)

    def write_coil(self, address: int, value: bool) -> bool:
        """Handle incoming Modbus FC 05 write coil."""
        if address == 0:  # Pusher command
            self.pusher_cmd = bool(value)
            self.pusher_transition_timer = 0.0
            return True
        elif address == 1:  # VFD Run command
            self.vfd_run_cmd = bool(value)
            return True
        elif address == 2:  # Shift counter reset
            if value:
                self.production_shift = 0
            return True
        return False

    def write_holding_register(self, address: int, value: int) -> bool:
        """Handle incoming Modbus FC 06 write register."""
        if address == 30:  # VFD Speed setpoint (in 0.1 Hz)
            # Clamp between 5.0 Hz and 50.0 Hz (50 - 500)
            clamped = max(50, min(500, value))
            self.vfd_speed_sp_hz = clamped / 10.0
            return True
        return False

    def read_discrete_input(self, address: int) -> bool:
        """Handle Modbus FC 02 read discrete inputs."""
        mapping = {
            0: self.belt_slip_active,
            1: self.pusher_extended_sensor if hasattr(self, 'pusher_extended_sensor') else self.pusher_extended,
            2: self.pusher_retracted_sensor if hasattr(self, 'pusher_retracted_sensor') else self.pusher_retracted,
            3: self.vfd_running,
            4: self.vfd_fault or (self.simulated_fault == "vfd_fault"),
            5: self.emergency_stop_ok,
            6: self.safety_guard_closed,
            7: self.part_sensor_active,
        }
        return mapping.get(address, False)

    def read_coils(self, address: int) -> bool:
        """Handle Modbus FC 01 read coils."""
        mapping = {
            0: self.pusher_cmd,
            1: self.vfd_run_cmd,
            2: False,
        }
        return mapping.get(address, False)


class SimulatedModbusServer:
    """
    Standalone Modbus TCP Server running on localhost:5020 for realistic
    end-to-end socket testing of PyModbus client.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5020):
        self.host = host
        self.port = port
        self.state = MockPlcState()
        self.server_task: Optional[asyncio.Task] = None
        self.physics_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def _physics_loop(self):
        """Continuous physics update tick."""
        last_time = time.perf_counter()
        while self._is_running:
            now = time.perf_counter()
            dt = now - last_time
            last_time = now
            self.state.update_physics(dt)
            await asyncio.sleep(0.05)  # 20 Hz simulation tick

    async def start(self):
        """Start physics engine and Modbus TCP server."""
        self._is_running = True
        self.physics_task = asyncio.create_task(self._physics_loop())
        logger.info(f"Simulated PLC physics engine started. Target port: {self.port}")

    async def stop(self):
        """Stop simulation."""
        self._is_running = False
        if self.physics_task:
            self.physics_task.cancel()
            try:
                await self.physics_task
            except asyncio.CancelledError:
                pass
        logger.info("Simulated PLC stopped.")


# Global simulation state singleton for direct in-process access
global_mock_plc = MockPlcState()
