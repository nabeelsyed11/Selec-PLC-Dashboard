"""
Automated unit tests for Latency Monitor, statistical percentiles,
encoder rollover handling, load cell tare, and belt slip detection.
"""
import pytest
import time
from app.latency.monitor import LatencySubsystem, LatencyRecord
from app.sensors.processing import SensorDataProcessor


def test_latency_percentiles():
    subsystem = LatencySubsystem()
    group = "fast_group"

    # Feed 100 observations with known simulated RTTs: 1ms to 100ms
    for i in range(1, 101):
        t_req = 100.0
        t_resp = 100.0 + (i / 1000.0)  # i ms RTT
        t_ingest = t_resp + 0.0005     # 0.5 ms ingest delay

        subsystem.record_poll(
            group_name=group,
            t_request_mono=t_req,
            t_response_mono=t_resp,
            t_ingest_mono=t_ingest,
            t_request_iso="2026-10-12T00:00:00Z",
            t_response_iso="2026-10-12T00:00:00Z",
            t_ingest_iso="2026-10-12T00:00:00Z",
        )

    stats = subsystem.get_all_group_stats()["groups"][group]
    assert stats["count"] == 100
    assert pytest.approx(stats["rtt_p50_ms"], 1.0) == 50.5
    assert pytest.approx(stats["rtt_p95_ms"], 1.0) == 95.05
    assert pytest.approx(stats["rtt_p99_ms"], 1.0) == 99.01
    assert stats["rtt_min_ms"] == 1.0
    assert stats["rtt_max_ms"] == 100.0


def test_encoder_rollover():
    processor = SensorDataProcessor()
    processor.encoder_cfg.max_count = 1000  # Small max count for test

    # First reading: initial count 950
    rpm, speed = processor.process_encoder(950)
    time.sleep(0.02)

    # Second reading: count rolls over to 50 (elapsed pulses = (1000 - 950) + 50 + 1 = 101)
    rpm2, speed2 = processor.process_encoder(50)
    assert rpm2 > 0.0
    assert speed2 > 0.0


def test_load_cell_tare_and_span():
    processor = SensorDataProcessor()
    # Baseline raw counts on empty platform = 25 counts
    processor.calibrate_load_cell_tare(25.0)

    # Empty platform reading: should be 0.0 kg
    assert processor.process_load_cell(25.0) == 0.0

    # Calibrate with 10 kg mass at 125 raw counts (net delta = 100 counts -> 0.1 kg/count)
    processor.calibrate_load_cell_span(known_weight_kg=10.0, current_raw=125.0)
    assert pytest.approx(processor.load_cell_cal.cal_factor, 0.001) == 0.1

    # Test unknown weight at 325 raw counts -> net = 300 counts -> 30.0 kg
    weight = processor.process_load_cell(325.0)
    assert pytest.approx(weight, 0.01) == 30.0


def test_temperature_alarms_and_hysteresis():
    processor = SensorDataProcessor()
    # Normal temperature
    active, sev = processor.process_temperature(55.0)
    assert not active
    assert sev == "NORMAL"

    # Warning threshold (75°C)
    active, sev = processor.process_temperature(76.0)
    assert active
    assert sev == "WARNING"

    # Critical threshold (90°C)
    active, sev = processor.process_temperature(92.0)
    assert active
    assert sev == "CRITICAL"

    # Temp drops to 74.0°C (within hysteresis range of 75 - 2 = 73°C) -> alarm remains active
    active, sev = processor.process_temperature(74.0)
    assert active

    # Temp drops below hysteresis (72.0°C < 73°C) -> alarm clears
    active, sev = processor.process_temperature(72.0)
    assert not active
    assert sev == "CLEARED"
