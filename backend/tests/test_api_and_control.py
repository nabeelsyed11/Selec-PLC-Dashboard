"""
Automated tests for FastAPI endpoints, safe control allowlists,
interlock rejections, and disabled-by-default remote control.
"""
import pytest
from starlette.testclient import TestClient
from app.core.config import settings

# Force simulation mode during API unit testing
settings.SIMULATION_MODE = True

from app.main import app


def test_api_system_telemetry():
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/system/telemetry")
        assert resp.status_code == 200
        data = resp.json()
        assert "cpu_percent" in data
        assert "uptime_seconds" in data


def test_api_latency_stats():
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/latency/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data


def test_safe_control_disabled_by_default():
    """Ensure remote control is strictly rejected with 403 when ALLOW_REMOTE_CONTROL is False."""
    settings.ALLOW_REMOTE_CONTROL = False
    with TestClient(app, raise_server_exceptions=False) as client:
        payload = {
            "command_name": "pusher_command",
            "target_value": 1.0,
            "operator_name": "operator",
            "operator_confirmed": True,
        }
        resp = client.post("/api/control/execute", json=payload)
        assert resp.status_code == 403
        assert "disabled by default" in resp.json()["detail"].lower()


def test_safe_control_unlisted_command_rejection():
    """Ensure write to an unlisted register name is immediately rejected."""
    settings.ALLOW_REMOTE_CONTROL = True
    with TestClient(app, raise_server_exceptions=False) as client:
        payload = {
            "command_name": "unauthorized_arbitrary_register",
            "target_value": 99.0,
            "operator_name": "intruder",
            "operator_confirmed": True,
        }
        resp = client.post("/api/control/execute", json=payload)
        assert resp.status_code == 400
        assert "not in the configured writable allowlist" in resp.json()["detail"]
    settings.ALLOW_REMOTE_CONTROL = False  # restore safe default
