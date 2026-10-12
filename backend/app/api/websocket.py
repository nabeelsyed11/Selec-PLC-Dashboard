"""
Real-time WebSocket Streaming Hub
Broadcasts live sensor signals, latency metrics, alarms, vibration FFT,
and telemetry to connected dashboard clients.
"""
import asyncio
from datetime import datetime, timezone
import json
import time
from typing import Set, Dict, Any, Optional
import logging
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("api.websocket")


class ConnectionManager:
    """Manages active browser WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_rtt_estimates: Dict[str, float] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, payload: Dict[str, Any]):
        """Broadcasts serialized JSON message to all active clients."""
        if not self.active_connections:
            return

        # Inject server publish timestamp
        t_publish_mono = time.perf_counter()
        t_publish_iso = datetime.now(timezone.utc).isoformat()
        payload["t_publish_mono"] = t_publish_mono
        payload["t_publish_iso"] = t_publish_iso

        raw_json = json.dumps(payload)
        dead_connections = set()

        for conn in self.active_connections:
            try:
                await conn.send_text(raw_json)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                dead_connections.add(conn)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()
