"""
SQLAlchemy Database Models for Industrial Measurements, Alarms,
Latency Observations, Production History, and Control Audit Logs.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Index
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SignalSnapshotModel(Base):
    """Current state snapshot for each monitored signal."""
    __tablename__ = "signals_snapshot"

    name = Column(String(64), primary_key=True)
    raw_value = Column(Float, nullable=False, default=0.0)
    engineering_value = Column(Float, nullable=False, default=0.0)
    engineering_unit = Column(String(32), default="")
    quality = Column(String(32), default="VALID")  # VALID, STALE, DISCONNECTED, SIMULATED
    group_name = Column(String(32), default="fast_group")
    updated_at_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    t_request_utc = Column(String(64), nullable=True)
    t_response_utc = Column(String(64), nullable=True)
    rtt_ms = Column(Float, default=0.0)


class MeasurementHistoryModel(Base):
    """Time-series measurement logs for historical trends."""
    __tablename__ = "measurements_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    signal_name = Column(String(64), index=True, nullable=False)
    value = Column(Float, nullable=False)
    quality = Column(String(32), default="VALID")

    __table_args__ = (
        Index("idx_meas_name_time", "signal_name", "timestamp_utc"),
    )


class LatencyObservationModel(Base):
    """Detailed latency observation records for historical analytics & benchmarking."""
    __tablename__ = "latency_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    group_name = Column(String(32), index=True, nullable=False)
    modbus_rtt_ms = Column(Float, nullable=False)
    ingestion_delay_ms = Column(Float, nullable=False)
    publish_delay_ms = Column(Float, default=0.0)
    render_delay_ms = Column(Float, nullable=True)
    end_to_end_latency_ms = Column(Float, nullable=True)
    data_age_ms = Column(Float, default=0.0)
    t_request_iso = Column(String(64))
    t_response_iso = Column(String(64))
    t_ingest_iso = Column(String(64))
    t_publish_iso = Column(String(64), nullable=True)
    t_render_iso = Column(String(64), nullable=True)


class AlarmRecordModel(Base):
    """Industrial alarm state records and operator acknowledgements."""
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), index=True, nullable=False)
    severity = Column(String(16), default="WARNING")  # INFO, WARNING, CRITICAL
    state = Column(String(16), default="ACTIVE", index=True)  # ACTIVE, ACKNOWLEDGED, CLEARED
    message = Column(Text, nullable=False)
    triggered_at_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    acknowledged_at_utc = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(64), nullable=True)
    cleared_at_utc = Column(DateTime, nullable=True)


class ControlAuditLogModel(Base):
    """Immutable audit trail for all remote control attempts and outcomes."""
    __tablename__ = "control_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    operator = Column(String(64), nullable=False)
    client_ip = Column(String(64), nullable=False)
    command_name = Column(String(64), nullable=False)
    target_address = Column(Integer, nullable=False)
    command_value = Column(Float, nullable=False)
    interlocks_verified = Column(Boolean, default=False)
    write_status = Column(String(32), nullable=False)  # SUCCESS, REJECTED, MODBUS_ERROR
    readback_verified = Column(Boolean, default=False)
    readback_value = Column(Float, nullable=True)
    feedback_sensor_verified = Column(Boolean, nullable=True)
    details = Column(Text, default="")


class ProductionHistoryModel(Base):
    """Periodic rollups for production counts, rate, and energy correlation."""
    __tablename__ = "production_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    shift_name = Column(String(32), default="Morning")
    total_count = Column(Integer, nullable=False)
    shift_count = Column(Integer, nullable=False)
    production_rate_ppm = Column(Float, default=0.0)
    cumulative_energy_kwh = Column(Float, default=0.0)
    energy_per_product_kwh = Column(Float, nullable=True)
