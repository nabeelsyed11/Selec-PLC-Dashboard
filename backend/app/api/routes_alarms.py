"""
Alarms and Events API Endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.machine.alarms import alarms_manager
from app.database.session import get_db_session
from app.database.models import AlarmRecordModel

router = APIRouter(prefix="/api/alarms", tags=["Alarms"])


class AcknowledgeRequest(BaseModel):
    operator_name: str = "operator"


@router.get("/active")
async def get_active_alarms():
    """Returns currently active and unacknowledged alarms."""
    return {"alarms": alarms_manager.get_active_list()}


@router.post("/clear-all")
async def clear_all_alarms():
    """Clears all active alarms."""
    alarms_manager.clear_all()
    return {"status": "cleared", "active_count": 0}


@router.post("/{name}/acknowledge")
async def acknowledge_alarm(name: str, req: AcknowledgeRequest):
    """Marks an active alarm as acknowledged by operator."""
    ok = alarms_manager.acknowledge_alarm(name, req.operator_name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Alarm '{name}' is not currently active.")
    return {"status": "acknowledged", "alarm_name": name, "by": req.operator_name}


@router.get("/history")
async def get_alarm_history(limit: int = 50, session: AsyncSession = Depends(get_db_session)):
    """Fetches historical alarms from database."""
    stmt = select(AlarmRecordModel).order_by(desc(AlarmRecordModel.triggered_at_utc)).limit(limit)
    res = await session.execute(stmt)
    records = res.scalars().all()
    return {
        "history": [
            {
                "id": r.id,
                "name": r.name,
                "severity": r.severity,
                "state": r.state,
                "message": r.message,
                "triggered_at": r.triggered_at_utc.isoformat(),
                "acknowledged_at": r.acknowledged_at_utc.isoformat() if r.acknowledged_at_utc else None,
                "acknowledged_by": r.acknowledged_by,
                "cleared_at": r.cleared_at_utc.isoformat() if r.cleared_at_utc else None,
            }
            for r in records
        ]
    }
