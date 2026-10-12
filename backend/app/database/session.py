"""
Asynchronous SQLite Database Session with WAL Mode and Buffered Inserts.
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, delete
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.database.models import Base, MeasurementHistoryModel, LatencyObservationModel

logger = logging.getLogger("database.session")

# Ensure data directory exists
Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)

# Create engine with SQLite WAL pragmas for high concurrent read/write throughput
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,
    },
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initializes tables and configures SQLite Write-Ahead Logging (WAL)."""
    async with engine.begin() as conn:
        # Enable WAL journal mode and normal synchronous for SSD/SD card life on Raspberry Pi 5
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA synchronous=NORMAL;"))
        await conn.execute(text("PRAGMA busy_timeout=5000;"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized with WAL mode and schema created.")


async def get_db_session():
    """Dependency for API endpoints."""
    async with async_session_factory() as session:
        yield session


class DatabaseBuffer:
    """
    Batches historical measurement and latency writes in memory and flushes
    periodically to disk (e.g. every 1.0 second) to prevent SD card burnout on Raspberry Pi 5.
    """

    def __init__(self, flush_interval_sec: float = 1.0):
        self.flush_interval_sec = flush_interval_sec
        self.meas_buffer: List[Dict[str, Any]] = []
        self.latency_buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self):
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
        await self.flush_now()

    def add_measurement(self, signal_name: str, value: float, quality: str = "VALID"):
        self.meas_buffer.append({
            "signal_name": signal_name,
            "value": float(value),
            "quality": quality,
            "timestamp_utc": datetime.now(timezone.utc),
        })

    def add_latency(self, latency_dict: Dict[str, Any]):
        self.latency_buffer.append(latency_dict)

    async def flush_now(self):
        """Immediately commits buffered items to SQLite."""
        async with self._lock:
            if not self.meas_buffer and not self.latency_buffer:
                return

            meas_to_insert = self.meas_buffer[:]
            latency_to_insert = self.latency_buffer[:]
            self.meas_buffer.clear()
            self.latency_buffer.clear()

        try:
            async with async_session_factory() as session:
                async with session.begin():
                    if meas_to_insert:
                        await session.run_sync(
                            lambda sync_sess: sync_sess.bulk_insert_mappings(
                                MeasurementHistoryModel, meas_to_insert
                            )
                        )
                    if latency_to_insert:
                        await session.run_sync(
                            lambda sync_sess: sync_sess.bulk_insert_mappings(
                                LatencyObservationModel, latency_to_insert
                            )
                        )
                await session.commit()
        except Exception as e:
            logger.error(f"Error flushing database buffer: {e}")

    async def _periodic_flush(self):
        while self._running:
            await asyncio.sleep(self.flush_interval_sec)
            await self.flush_now()

    async def prune_old_data(self, retention_hours: int = 720):
        """Deletes historical records older than retention threshold."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    await session.execute(
                        delete(MeasurementHistoryModel).where(
                            MeasurementHistoryModel.timestamp_utc < cutoff
                        )
                    )
                    await session.execute(
                        delete(LatencyObservationModel).where(
                            LatencyObservationModel.timestamp_utc < cutoff
                        )
                    )
                await session.commit()
            logger.info(f"Pruned historical database records older than {retention_hours} hours.")
        except Exception as e:
            logger.error(f"Error pruning old database data: {e}")


db_buffer = DatabaseBuffer(flush_interval_sec=settings.MEASUREMENT_BUFFER_FLUSH_SEC)
