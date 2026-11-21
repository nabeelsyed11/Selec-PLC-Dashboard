"""
Signals API Endpoints: Live Snapshots and Historical Query.
"""
from fastapi import APIRouter, Query, Depends
from typing import Dict, Any, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.database.session import get_db_session
from app.database.models import MeasurementHistoryModel

router = APIRouter(prefix="/api/signals", tags=["Signals"])


@router.get("/snapshot")
async def get_signals_snapshot():
    """Returns current cached snapshot of all monitored signals."""
    from app.main import app_state
    return {
        "signals": app_state.signals_snapshot,
        "machine_state": app_state.current_machine_state,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
async def get_signal_history(
    signal_name: str = Query(..., description="Name of signal"),
    minutes: int = Query(30, description="History window in minutes"),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieves time-series historical points for trend charts."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stmt = (
        select(MeasurementHistoryModel)
        .where(
            MeasurementHistoryModel.signal_name == signal_name,
            MeasurementHistoryModel.timestamp_utc >= cutoff,
        )
        .order_by(MeasurementHistoryModel.timestamp_utc.desc())
        .limit(1000)
    )
    result = await session.execute(stmt)
    records = list(result.scalars().all())
    records.reverse()  # Chronological order for frontend charting

    return {
        "signal_name": signal_name,
        "points": [
            {
                "timestamp": r.timestamp_utc.isoformat() if r.timestamp_utc.tzinfo else r.timestamp_utc.replace(tzinfo=timezone.utc).isoformat(),
                "value": r.value,
                "quality": r.quality,
            }
            for r in records
        ],
    }
