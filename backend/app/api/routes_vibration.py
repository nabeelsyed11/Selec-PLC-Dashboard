"""
Vibration Analytics API Endpoints.
"""
from fastapi import APIRouter
from app.vibration.sensor import vibration_engine

router = APIRouter(prefix="/api/vibration", tags=["Vibration"])


@router.get("/live")
async def get_live_vibration():
    """Returns current vibration metrics, time-domain waveform, and FFT spectrum."""
    return vibration_engine.get_latest_payload()
