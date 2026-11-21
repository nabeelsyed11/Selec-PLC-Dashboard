"""
Safe Machine Remote Control API Endpoints.
Enforces allowlist check, interlock verification, confirmation modal, and audit logs.
"""
import math
import re
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.control.service import safe_control_service
from app.database.session import get_db_session
from app.database.models import ControlAuditLogModel
from app.core.config import settings

router = APIRouter(prefix="/api/control", tags=["Control"])

OPERATOR_REGEX = re.compile(r"^[a-zA-Z0-9_\- ]{1,32}$")


class ControlCommandRequest(BaseModel):
    command_name: str
    target_value: float
    operator_name: str = Field("operator", max_length=32)
    operator_confirmed: bool = False

    @field_validator("operator_name")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned or not OPERATOR_REGEX.match(cleaned):
            raise ValueError("Operator name must be 1-32 alphanumeric characters.")
        return cleaned


@router.get("/allowlist")
async def get_writable_allowlist():
    """Returns the list of explicitly configured writable registers/coils and safety state."""
    return {
        "remote_control_globally_enabled": settings.ALLOW_REMOTE_CONTROL,
        "allowlist": [
            {
                "name": e.name,
                "address": e.address,
                "function_code": e.function_code,
                "description": e.description,
                "min_value": e.min_value,
                "max_value": e.max_value,
                "requires_interlock": e.requires_interlock,
                "confirmation_required": e.confirmation_required,
            }
            for e in safe_control_service.reg_map.writable_allowlist
        ],
    }


@router.post("/execute")
async def execute_command(req: ControlCommandRequest, request: Request):
    """Executes validated, allowlisted remote control request."""
    from app.main import app_state

    # 1. Enforce finite target value
    if math.isnan(req.target_value) or math.isinf(req.target_value):
        raise HTTPException(status_code=400, detail="Target value must be a valid, finite number.")

    # 2. Enforce global remote control policy
    if not settings.ALLOW_REMOTE_CONTROL:
        raise HTTPException(
            status_code=403,
            detail="Remote machine control is disabled by default (ALLOW_REMOTE_CONTROL=false).",
        )

    # 3. Validate control token if custom secret is configured
    if settings.CONTROL_TOKEN_SECRET and settings.CONTROL_TOKEN_SECRET not in ("default-insecure-dev-key-change-in-production", "change-this-in-production-to-a-secure-random-key-64chars"):
        token = request.headers.get("X-Control-Token")
        if token != settings.CONTROL_TOKEN_SECRET:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing X-Control-Token header.")

    client_ip = request.client.host if request.client else "127.0.0.1"

    result = await safe_control_service.execute_control_request(
        modbus_client=app_state.modbus_client,
        operator=req.operator_name,
        client_ip=client_ip,
        command_name=req.command_name,
        target_value=req.target_value,
        current_signals=app_state.signals_snapshot,
        operator_confirmed=req.operator_confirmed,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=403 if result.get("status") == "DISABLED" else 400,
            detail=result.get("message"),
        )

    return result


@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50, session: AsyncSession = Depends(get_db_session)):
    """Retrieves immutable audit trail of past remote control attempts."""
    stmt = select(ControlAuditLogModel).order_by(desc(ControlAuditLogModel.timestamp_utc)).limit(limit)
    res = await session.execute(stmt)
    records = res.scalars().all()
    return {
        "audit_logs": [
            {
                "id": r.id,
                "timestamp": r.timestamp_utc.isoformat(),
                "operator": r.operator,
                "client_ip": r.client_ip,
                "command_name": r.command_name,
                "target_address": r.target_address,
                "command_value": r.command_value,
                "interlocks_verified": r.interlocks_verified,
                "status": r.write_status,
                "readback_verified": r.readback_verified,
                "readback_value": r.readback_value,
                "details": r.details,
            }
            for r in records
        ]
    }
