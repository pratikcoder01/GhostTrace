import pytest
import asyncio
from unittest.mock import AsyncMock
from backend.app.api.ws import ConnectionManager
from backend.app.schemas import WebSocketMessage

@pytest.mark.anyio
async def test_ws_case_isolation():
    manager = ConnectionManager()
    
    # Mock two client websockets
    ws_case_a = AsyncMock()
    ws_case_b = AsyncMock()
    
    await manager.connect(ws_case_a)
    await manager.connect(ws_case_b)
    
    # Subscribe ws_case_a to CASE-A and ws_case_b to CASE-B
    await manager.subscribe(ws_case_a, "CASE-A")
    await manager.subscribe(ws_case_b, "CASE-B")
    
    msg_a = WebSocketMessage(
        event_id="evt_01",
        type="graph.updated",
        timestamp="2026-01-01T00:00:00Z",
        case_id="CASE-A",
        data={"nodes": 5}
    )
    
    # Broadcast to CASE-A
    await manager.broadcast_to_case("CASE-A", msg_a)
    
    # ws_case_a should receive message
    assert ws_case_a.send_text.called
    # ws_case_b should NOT receive message because it is only subscribed to CASE-B
    assert not ws_case_b.send_text.called
