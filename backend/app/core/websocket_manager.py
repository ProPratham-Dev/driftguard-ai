import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from fastapi import WebSocket

logger = logging.getLogger("driftguard.websocket")

class WebSocketConnectionManager:
    """
    Thread-safe, non-blocking WebSocket connection manager.
    Broadcasts real-time events to all active dashboard clients,
    safely handling disconnected or slow clients without blocking others.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection and track it."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection safely."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """
        Broadcast structured event to all active clients.
        Each send is guarded with a timeout to prevent slow clients from stalling the engine.
        """
        if not self.active_connections:
            return

        message = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        text_payload = json.dumps(message, default=str)
        connections = list(self.active_connections)

        dead_connections: List[WebSocket] = []

        async def _safe_send(ws: WebSocket):
            try:
                # 1.5s timeout per client send
                await asyncio.wait_for(ws.send_text(text_payload), timeout=1.5)
            except Exception as e:
                logger.warning(f"Failed to send to client ({e}); marking for removal.")
                dead_connections.append(ws)

        await asyncio.gather(*[_safe_send(ws) for ws in connections], return_exceptions=True)

        for dead_ws in dead_connections:
            self.active_connections.discard(dead_ws)

    def client_count(self) -> int:
        return len(self.active_connections)

# Global singleton
ws_manager = WebSocketConnectionManager()
