"""WebSocket endpoint for real-time price & signal streaming."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime_service import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """Stream live price updates and strategy signals to the browser.

    Connect once; receive JSON messages of two types::

        # Real-time price tick (every ~15 s)
        {"type": "price_update",
         "data": {"RELIANCE": {"price": 1234.5, "change_pct": 0.32, ...}, ...},
         "timestamp": "<iso>"}

        # Strategy signal (every ~60 s, watchlist symbols only)
        {"type": "strategy_signal",
         "data": {"symbol": "RELIANCE", "signal": "BUY", "confidence": 0.8, ...},
         "timestamp": "<iso>"}

    The client may send any text frame to keep the connection alive (ping).
    """
    await manager.connect(websocket)
    try:
        while True:
            # Block until the client sends a frame (heartbeat / ping) or
            # disconnects.  We don't act on the data; it just keeps the loop
            # alive so FastAPI doesn't tear down the coroutine.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
