"""
Latency Monitoring and Benchmark API Endpoints.
"""
from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.latency.monitor import latency_subsystem

router = APIRouter(prefix="/api/latency", tags=["Latency"])


class BenchmarkRequest(BaseModel):
    duration_seconds: int = 60
    group_name: str = "fast_group"


@router.get("/stats")
async def get_latency_stats():
    """Returns rolling latency statistics and percentile breakdowns for all groups."""
    return latency_subsystem.get_all_group_stats()


@router.post("/benchmark/start")
async def start_benchmark(req: BenchmarkRequest):
    """Initiates an active latency benchmark run."""
    latency_subsystem.start_benchmark(
        duration_sec=float(req.duration_seconds),
        group=req.group_name
    )
    return {
        "status": "started",
        "duration_seconds": req.duration_seconds,
        "group_name": req.group_name,
    }


@router.post("/benchmark/stop")
async def stop_benchmark():
    """Terminates an ongoing latency benchmark run."""
    latency_subsystem.stop_benchmark()
    return {"status": "stopped"}


@router.get("/benchmark/export")
async def export_benchmark_csv():
    """Exports benchmark measurements as CSV download."""
    csv_content = latency_subsystem.export_benchmark_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=selec_plc_latency_benchmark.csv"
        },
    )
