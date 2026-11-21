"""
Industrial Alarms and Event Management Engine.
Handles active alarms, transitions, operator acknowledgements, and severity levels.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

from app.database.session import async_session_factory
from app.database.models import AlarmRecordModel
from sqlalchemy import select, update

logger = logging.getLogger("machine.alarms")


class AlarmItem:
    def __init__(self, name: str, severity: str, message: str):
        self.name = name
        self.severity = severity  # INFO, WARNING, CRITICAL
        self.message = message
        self.state = "ACTIVE"     # ACTIVE, ACKNOWLEDGED, CLEARED
        self.triggered_at_iso = datetime.now(timezone.utc).isoformat()
        self.acknowledged_at_iso: Optional[str] = None
        self.acknowledged_by: Optional[str] = None


SEVERITY_LEVELS = {"INFO": 1, "WARNING": 2, "CRITICAL": 3}


class AlarmsManager:
    """In-memory active alarms cache synchronized with SQLite records."""

    def __init__(self):
        self.active_alarms: Dict[str, AlarmItem] = {}

    def trigger_alarm(self, name: str, severity: str, message: str) -> bool:
        """
        Triggers or escalates an active alarm.
        Returns True if a new alarm was raised or an existing alarm was escalated.
        """
        now_dt = datetime.now(timezone.utc)
        if name in self.active_alarms:
            existing = self.active_alarms[name]
            current_lvl = SEVERITY_LEVELS.get(existing.severity.upper(), 1)
            new_lvl = SEVERITY_LEVELS.get(severity.upper(), 1)
            if new_lvl > current_lvl:
                existing.severity = severity.upper()
                existing.message = message
                logger.warning(f"ALARM ESCALATED: [{existing.severity}] {name} - {message}")
                try:
                    from app.database.session import db_buffer
                    db_buffer.add_alarm({
                        "name": name,
                        "severity": existing.severity,
                        "state": existing.state,
                        "message": message,
                        "triggered_at_utc": now_dt,
                    })
                except Exception:
                    pass
                return True
            return False

        alarm = AlarmItem(name=name, severity=severity, message=message)
        self.active_alarms[name] = alarm
        logger.warning(f"ALARM TRIGGERED: [{severity}] {name} - {message}")
        try:
            from app.database.session import db_buffer
            db_buffer.add_alarm({
                "name": name,
                "severity": severity,
                "state": "ACTIVE",
                "message": message,
                "triggered_at_utc": now_dt,
            })
        except Exception:
            pass
        return True

    def clear_alarm(self, name: str) -> bool:
        """Clears an alarm if active."""
        if name in self.active_alarms:
            existing = self.active_alarms.pop(name)
            logger.info(f"ALARM CLEARED: {name}")
            try:
                from app.database.session import db_buffer
                db_buffer.add_alarm({
                    "name": name,
                    "severity": existing.severity,
                    "state": "CLEARED",
                    "message": f"Cleared: {existing.message}",
                    "triggered_at_utc": datetime.fromisoformat(existing.triggered_at_iso),
                    "cleared_at_utc": datetime.now(timezone.utc),
                })
            except Exception:
                pass
            return True
        return False

    def acknowledge_alarm(self, name: str, operator_name: str) -> bool:
        """Acknowledges an active alarm by an authorized operator."""
        if name in self.active_alarms:
            alarm = self.active_alarms[name]
            alarm.state = "ACKNOWLEDGED"
            alarm.acknowledged_at_iso = datetime.now(timezone.utc).isoformat()
            alarm.acknowledged_by = operator_name
            logger.info(f"ALARM ACKNOWLEDGED: {name} by {operator_name}")
            try:
                from app.database.session import db_buffer
                db_buffer.add_alarm({
                    "name": name,
                    "severity": alarm.severity,
                    "state": "ACKNOWLEDGED",
                    "message": alarm.message,
                    "triggered_at_utc": datetime.fromisoformat(alarm.triggered_at_iso),
                    "acknowledged_at_utc": datetime.now(timezone.utc),
                    "acknowledged_by": operator_name,
                })
            except Exception:
                pass
            return True
        return False

    def clear_all(self):
        """Clears all active alarms."""
        self.active_alarms.clear()
        logger.info("ALL ACTIVE ALARMS CLEARED")

    def has_critical(self) -> bool:
        return any(a.severity == "CRITICAL" for a in self.active_alarms.values())

    def get_active_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": a.name,
                "severity": a.severity,
                "message": a.message,
                "state": a.state,
                "triggered_at": a.triggered_at_iso,
                "acknowledged_at": a.acknowledged_at_iso,
                "acknowledged_by": a.acknowledged_by,
            }
            for a in self.active_alarms.values()
        ]


alarms_manager = AlarmsManager()
