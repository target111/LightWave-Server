from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from lib.api.broadcast import FrameBroadcaster

router = APIRouter()


@router.websocket("/ws")
async def state_stream(websocket: WebSocket):
    """Streams the strip state whenever it changes, throttled
    server-side: binary pixel frames (1 brightness byte + 3 bytes per
    LED) plus JSON status messages when the running preset changes."""
    broadcaster: FrameBroadcaster = websocket.app.state.broadcaster
    await broadcaster.connect(websocket)
    try:
        while True:
            # Clients don't send anything meaningful; this just parks the
            # handler until the socket closes.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.disconnect(websocket)
