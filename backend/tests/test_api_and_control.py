"""
Automated unit tests for system diagnostics, latency monitors,
safe control allowlists, input sanitization, and security validations.
"""
import pytest
from app.core.config import settings
from app.machine.state import machine_state_manager
from app.latency.monitor import latency_subsystem
from app.control.service import safe_control_service
from app.api.routes_control import ControlCommandRequest
from app.api.routes_system import PLCConfigSchema, PLCTestRequest


def test_api_system_telemetry():
    """Ensure system telemetry returns valid hardware resource metrics."""
    data = machine_state_manager.get_system_telemetry()
    assert "cpu_percent" in data
    assert "uptime_seconds" in data
    assert "memory_percent" in data
    assert "disk_percent" in data
    assert isinstance(data["uptime_seconds"], int)
    assert 0.0 <= data["memory_percent"] <= 100.0


def test_api_latency_stats():
    """Ensure latency monitoring subsystem exposes configured signal groups."""
    latency_subsystem.record_poll(
        group_name="fast_group",
        t_request_mono=100.0,
        t_response_mono=100.005,
        t_ingest_mono=100.006,
        t_request_iso="2026-10-12T00:00:00Z",
        t_response_iso="2026-10-12T00:00:00Z",
        t_ingest_iso="2026-10-12T00:00:00Z",
    )
    data = latency_subsystem.get_all_group_stats()
    assert "groups" in data
    assert "fast_group" in data["groups"]


def test_latency_record_has_data_age():
    """Ensure LatencyRecord has data_age_ms property and does not raise AttributeError."""
    rec = latency_subsystem.record_poll(
        group_name="fast_group",
        t_request_mono=100.0,
        t_response_mono=100.010,
        t_ingest_mono=100.015,
        t_request_iso="2026-10-12T00:00:00Z",
        t_response_iso="2026-10-12T00:00:00Z",
        t_ingest_iso="2026-10-12T00:00:00Z",
    )
    assert hasattr(rec, "data_age_ms")
    assert pytest.approx(rec.data_age_ms, 0.1) == 15.0


def test_safe_control_allowlist_configuration():
    """Ensure only explicitly allowlisted commands can be executed."""
    assert len(safe_control_service.allowlist) > 0
    assert "pusher_command" in safe_control_service.allowlist
    assert "unauthorized_arbitrary_register" not in safe_control_service.allowlist


def test_safe_control_disabled_by_default():
    """Ensure ALLOW_REMOTE_CONTROL is safely False by default."""
    assert settings.ALLOW_REMOTE_CONTROL is False


def test_control_input_validation_and_sanitization():
    """Ensure invalid operator names and illegal target values are rejected."""
    # Valid request
    req = ControlCommandRequest(
        command_name="pusher_command",
        target_value=1.0,
        operator_name="operator_1",
        operator_confirmed=True,
    )
    assert req.operator_name == "operator_1"

    # Invalid operator name with injection characters
    with pytest.raises(ValueError):
        ControlCommandRequest(
            command_name="pusher_command",
            target_value=1.0,
            operator_name="operator; rm -rf /",
            operator_confirmed=True,
        )


def test_system_config_host_injection_prevention():
    """Ensure newline and command injection in PLC host configuration is rejected."""
    # Valid host
    valid_cfg = PLCConfigSchema(plc_host="192.168.1.50")
    assert valid_cfg.plc_host == "192.168.1.50"

    # Malicious host with newline injection
    with pytest.raises(ValueError):
        PLCConfigSchema(plc_host="127.0.0.1\nCONTROL_TOKEN_SECRET=pwned")

    # Malicious host in test request
    with pytest.raises(ValueError):
        PLCTestRequest(plc_host="127.0.0.1\nALLOW_REMOTE_CONTROL=true")
