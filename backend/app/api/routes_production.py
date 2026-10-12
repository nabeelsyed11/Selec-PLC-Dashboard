"""
Production OEE & Load Cell Calibration API Endpoints.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

from app.sensors.processing import SensorDataProcessor

router = APIRouter(prefix="/api/production", tags=["Production"])


class TareRequest(BaseModel):
    raw_counts: float = 0.0


class SpanCalRequest(BaseModel):
    known_weight_kg: float
    raw_counts: float


@router.post("/tare-loadcell")
async def tare_load_cell(req: TareRequest):
    """Sets current raw counts as zero tare reference."""
    from app.main import app_state
    raw = req.raw_counts or app_state.signals_snapshot.get("load_cell_weight", {}).get("raw_value", 0.0)
    app_state.sensor_processor.calibrate_load_cell_tare(raw)
    return {"status": "success", "zero_tare_raw": raw}


@router.post("/calibrate-span")
async def calibrate_span(req: SpanCalRequest):
    """Calibrates load cell scale factor from a known test mass."""
    from app.main import app_state
    app_state.sensor_processor.calibrate_load_cell_span(req.known_weight_kg, req.raw_counts)
    return {
        "status": "success",
        "cal_factor": app_state.sensor_processor.load_cell_cal.cal_factor,
        "test_mass_kg": req.known_weight_kg,
    }
