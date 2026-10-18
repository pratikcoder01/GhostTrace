import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.schemas import WebSocketMessage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

class ConnectionManager:
    """
    Manages active WebSocket connections, case-specific subscriptions,
    heartbeats, and bounded async message distribution.
    """
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.case_subscriptions: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            for case_id, subs in list(self.case_subscriptions.items()):
                if websocket in subs:
                    subs.remove(websocket)
                if not subs:
                    self.case_subscriptions.pop(case_id, None)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def subscribe(self, websocket: WebSocket, case_id: str):
        async with self._lock:
            if case_id not in self.case_subscriptions:
                self.case_subscriptions[case_id] = set()
            self.case_subscriptions[case_id].add(websocket)
        logger.info(f"Client subscribed to case '{case_id}'.")

    async def unsubscribe(self, websocket: WebSocket, case_id: str):
        async with self._lock:
            if case_id in self.case_subscriptions and websocket in self.case_subscriptions[case_id]:
                self.case_subscriptions[case_id].remove(websocket)
        logger.info(f"Client unsubscribed from case '{case_id}'.")

    async def broadcast(self, message: WebSocketMessage):
        """Broadcasts a typed message to all active clients."""
        payload_str = message.model_dump_json()
        async with self._lock:
            clients = list(self.active_connections)

        for client in clients:
            try:
                await asyncio.wait_for(client.send_text(payload_str), timeout=2.0)
            except Exception:
                # Disconnect slow or failed clients safely
                await self.disconnect(client)

    async def broadcast_to_case(self, case_id: str, message: WebSocketMessage):
        """Sends message to clients specifically subscribed to case_id."""
        payload_str = message.model_dump_json()
        async with self._lock:
            target_clients = set(self.case_subscriptions.get(case_id, set()))
            clients = list(target_clients)

        for client in clients:
            try:
                await asyncio.wait_for(client.send_text(payload_str), timeout=2.0)
            except Exception:
                await self.disconnect(client)

    async def broadcast_global_and_case(self, case_id: str, message: WebSocketMessage):
        """Sends message to clients specifically subscribed to case_id PLUS global listeners."""
        payload_str = message.model_dump_json()
        async with self._lock:
            target_clients = set(self.case_subscriptions.get(case_id, set()))
            target_clients.update(self.active_connections)
            clients = list(target_clients)

        for client in clients:
            try:
                await asyncio.wait_for(client.send_text(payload_str), timeout=2.0)
            except Exception:
                await self.disconnect(client)

ws_manager = ConnectionManager()

@router.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)

    # Send initial connection acknowledgment snapshot
    ack_msg = WebSocketMessage(
        event_id=f"ack_{datetime.now(timezone.utc).timestamp()}",
        type="connection.ack",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={
            "status": "connected",
            "message": "GhostTrace real-time event stream connected.",
            "heartbeat_interval_seconds": 15
        }
    )
    await websocket.send_text(ack_msg.model_dump_json())

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                msg_type = data.get("type", "").lower()

                # Heartbeat
                if msg_type == "ping":
                    pong = WebSocketMessage(
                        event_id=f"pong_{datetime.now(timezone.utc).timestamp()}",
                        type="pong",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        data={"client_timestamp": data.get("timestamp")}
                    )
                    await websocket.send_text(pong.model_dump_json())

                # Case Subscriptions
                elif msg_type == "subscribe":
                    case_id = data.get("case_id")
                    if case_id:
                        await ws_manager.subscribe(websocket, case_id)
                        resp = WebSocketMessage(
                            event_id=f"sub_ack_{case_id}",
                            type="subscription.ack",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            case_id=case_id,
                            data={"subscribed": True, "case_id": case_id}
                        )
                        await websocket.send_text(resp.model_dump_json())

                elif msg_type == "unsubscribe":
                    case_id = data.get("case_id")
                    if case_id:
                        await ws_manager.unsubscribe(websocket, case_id)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        await ws_manager.disconnect(websocket)
