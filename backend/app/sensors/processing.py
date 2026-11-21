"""
Industrial Sensor Processing, Calibration, Rollover Handling,
and Engineering Unit Conversions.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import time
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger("sensors.processing")


@dataclass
class LoadCellCalibration:
    zero_tare_raw: float = 0.0
    cal_factor: float = 0.1     # kg per raw count
    capacity_kg: float = 500.0


@dataclass
class EncoderConfig:
    pulses_per_rev: int = 1024
    gear_ratio: float = 12.0    # 12:1 motor-to-roller gearbox
    roller_diameter_m: float = 0.10
    max_count: int = 4294967295 # 32-bit UINT rollover


class SensorDataProcessor:
    """
    Maintains sensor state, rollover tracking, calibrations,
    and alarm conditions.
    """

    def __init__(self):
        # Load cell
        self.load_cell_cal = LoadCellCalibration()

        # Encoder tracking
        self.encoder_cfg = EncoderConfig()
        self.last_encoder_raw: Optional[int] = None
        self.last_encoder_mono: float = 0.0
        self.current_rpm: float = 0.0
        self.current_belt_speed_mps: float = 0.0

        # Production tracking
        self.last_prod_total: Optional[int] = None
        self.last_prod_mono: float = 0.0
        self.production_shift_count: int = 0
        self.shift_start_total: int = 0
        self.production_rate_ppm: float = 0.0
        self.hourly_counts: List[Dict[str, Any]] = []

        # Temperature limits
        self.temp_warning_limit: float = 75.0
        self.temp_critical_limit: float = 90.0
        self.temp_alarm_hysteresis: float = 2.0
        self.temp_alarm_active: bool = False

        # Belt slip tracking
        self.belt_slip_active: bool = False
        self.belt_slip_start_mono: Optional[float] = None
        self.belt_slip_duration_sec: float = 0.0

        # Pusher actuator feedback verification
        self.pusher_cmd_active: bool = False
        self.pusher_cmd_time_mono: Optional[float] = None
        self.pusher_mismatch_alarm: bool = False
        self.pusher_feedback_timeout_sec: float = 1.5

    def calibrate_load_cell_tare(self, raw_counts: float):
        """Sets current raw counts as the new zero tare reference."""
        self.load_cell_cal.zero_tare_raw = float(raw_counts)
        logger.info(f"Load cell zero tare set to {raw_counts} raw counts.")

    def calibrate_load_cell_span(self, known_weight_kg: float, current_raw: float):
        """Calculates and updates cal_factor from a known test mass."""
        delta_raw = current_raw - self.load_cell_cal.zero_tare_raw
        if abs(delta_raw) < 1.0:
            raise ValueError("Zero delta: cannot calibrate with zero raw counts")
        self.load_cell_cal.cal_factor = known_weight_kg / delta_raw
        logger.info(f"Load cell calibrated: factor={self.load_cell_cal.cal_factor:.6f} kg/count")

    def process_load_cell(self, raw_value: float) -> float:
        """Computes calibrated weight using zero tare and cal factor."""
        net_raw = raw_value - self.load_cell_cal.zero_tare_raw
        calibrated_kg = net_raw * self.load_cell_cal.cal_factor
        return max(0.0, round(calibrated_kg, 2))

    def process_encoder(self, raw_count: int) -> Tuple[float, float]:
        """
        Calculates RPM and linear belt speed with rollover protection.
        Returns (rpm: float, belt_speed_mps: float).
        """
        now_mono = time.perf_counter()

        if self.last_encoder_raw is None:
            self.last_encoder_raw = raw_count
            self.last_encoder_mono = now_mono
            return 0.0, 0.0

        dt = now_mono - self.last_encoder_mono
        if dt <= 0.001:
            return self.current_rpm, self.current_belt_speed_mps

        # Rollover check vs counter reset check
        if raw_count >= self.last_encoder_raw:
            delta_pulses = raw_count - self.last_encoder_raw
        else:
            # Genuine rollover only occurs when last_encoder_raw was near max_count (4294967295)
            # If last_encoder_raw dropped due to counter reset or failed read returning 0,
            # treating as rollover calculates billions of pulses.
            if self.last_encoder_raw > (self.encoder_cfg.max_count - 100000):
                delta_pulses = (self.encoder_cfg.max_count - self.last_encoder_raw) + raw_count + 1
            else:
                delta_pulses = 0

        self.last_encoder_raw = raw_count
        self.last_encoder_mono = now_mono

        # Pulses per second
        pulses_per_sec = delta_pulses / dt
        # Roller RPM = (pulses_per_sec / pulses_per_rev) * 60, clamped to reasonable industrial limit
        roller_rpm = min(10000.0, max(0.0, (pulses_per_sec / self.encoder_cfg.pulses_per_rev) * 60.0))
        # Motor RPM = roller_rpm * gear_ratio
        motor_rpm = roller_rpm * self.encoder_cfg.gear_ratio

        # Linear speed: v = (roller_rpm / 60) * (pi * D)
        roller_circ_m = math.pi * self.encoder_cfg.roller_diameter_m
        speed_mps = (roller_rpm / 60.0) * roller_circ_m

        self.current_rpm = round(roller_rpm, 1)
        self.current_belt_speed_mps = round(speed_mps, 2)
        return self.current_rpm, self.current_belt_speed_mps

    def process_temperature(self, temp_c: float) -> Tuple[bool, str]:
        """
        Evaluates motor temperature against warning/critical thresholds
        with alarm hysteresis.
        Returns (alarm_active: bool, severity: str).
        """
        if temp_c >= self.temp_critical_limit:
            self.temp_alarm_active = True
            return True, "CRITICAL"
        elif temp_c >= self.temp_warning_limit:
            self.temp_alarm_active = True
            return True, "WARNING"
        elif self.temp_alarm_active and temp_c < (self.temp_warning_limit - self.temp_alarm_hysteresis):
            self.temp_alarm_active = False
            return False, "CLEARED"
        return self.temp_alarm_active, "NORMAL"

    def process_belt_slip(
        self, sensor_state: int, vfd_speed_hz: float, encoder_speed_mps: float
    ) -> Tuple[bool, float]:
        """
        Evaluates belt slip based on physical proximity sensor AND speed ratio.
        Returns (slip_active: bool, duration_sec: float).
        """
        now = time.perf_counter()
        ratio_slip = (vfd_speed_hz > 15.0 and encoder_speed_mps < 0.05)
        is_slipping = bool(sensor_state == 1 or ratio_slip)

        if is_slipping:
            if not self.belt_slip_active:
                self.belt_slip_active = True
                self.belt_slip_start_mono = now
            self.belt_slip_duration_sec = now - self.belt_slip_start_mono
        else:
            self.belt_slip_active = False
            self.belt_slip_start_mono = None
            self.belt_slip_duration_sec = 0.0

        return self.belt_slip_active, round(self.belt_slip_duration_sec, 2)

    def process_pusher_feedback(
        self, cmd_active: bool, extended_feedback: int, retracted_feedback: int
    ) -> Tuple[bool, str]:
        """
        Verifies actuator physical sensor feedback matches commanded output.
        Returns (mismatch_alarm: bool, status_message: str).
        """
        now = time.perf_counter()

        if cmd_active != self.pusher_cmd_active:
            # Transition occurred
            self.pusher_cmd_active = cmd_active
            self.pusher_cmd_time_mono = now
            self.pusher_mismatch_alarm = False

        if self.pusher_cmd_time_mono is not None:
            elapsed = now - self.pusher_cmd_time_mono
            if elapsed > self.pusher_feedback_timeout_sec:
                if self.pusher_cmd_active and not extended_feedback:
                    self.pusher_mismatch_alarm = True
                    return True, "ALARM: Pusher commanded extend, but extended sensor not detected!"
                elif not self.pusher_cmd_active and not retracted_feedback:
                    self.pusher_mismatch_alarm = True
                    return True, "ALARM: Pusher commanded retract, but retracted sensor not detected!"

        return False, "OK"
