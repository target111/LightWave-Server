import asyncio
import contextlib
import logging
from itertools import chain

from fastapi import WebSocket

from lib.services.effect import EffectService

logger = logging.getLogger(__name__)


class FrameBroadcaster:
    """Fans out LED state to websocket clients.

    Effect threads and API handlers call `notify()` (cheap and
    thread-safe) via `LEDController.on_change` (pixel writes) and
    `EffectService.on_state_change` (effect started/stopped/died) — both
    wired up in the app lifespan; an asyncio task coalesces those
    wake-ups, snapshots the controller, and pushes one frame to every
    client, throttled to `fps`.

    Wire protocol: pixel frames are binary — one brightness byte
    (0-255) followed by 3 bytes (RGB) per LED. The running effect (and
    the preset it was started from, if any) is sent as a JSON text
    message, only on connect and when it changes."""

    def __init__(self, service: EffectService, fps: int = 30):
        self._service = service
        self._fps = fps
        self._clients: set[WebSocket] = set()
        self._dirty = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Begin broadcasting. Must be called from the running event loop."""
        self._loop = asyncio.get_running_loop()
        self._task = self._loop.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def notify(self) -> None:
        """Mark the frame dirty. Safe to call from any thread."""
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._dirty.set)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        # Push the current state right away so a new client doesn't sit
        # on a blank strip until something changes.
        with contextlib.suppress(Exception):
            await websocket.send_json(self._status())
            await websocket.send_bytes(self._frame())

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    def _status(self) -> dict:
        """The status payload, which doubles as the change key: a change
        in either the running effect or its preset (starting the same
        effect from a different preset included) pushes a fresh status."""
        return {
            "type": "status",
            "running": self._service.running_name,
            "preset": self._service.running_preset,
        }

    def _frame(self) -> bytes:
        pixels, brightness = self._service.controller.snapshot()
        return bytes([round(brightness * 255), *chain.from_iterable(pixels)])

    async def _run(self) -> None:
        frame_time = 1.0 / self._fps
        last_status = self._status()
        while True:
            await self._dirty.wait()
            self._dirty.clear()

            try:
                status = self._status()
                if status != last_status:
                    last_status = status
                    await self._send_all(status)
                if self._clients:
                    await self._send_all(self._frame())
            except asyncio.CancelledError:
                raise
            except Exception:
                # A bad frame must not kill broadcasting for everyone.
                logger.exception("frame broadcast failed")
            await asyncio.sleep(frame_time)

    async def _send_all(self, message: dict | bytes) -> None:
        # Snapshot: sends run concurrently, and a client connecting or
        # disconnecting meanwhile would mutate the set mid-iteration.
        clients = tuple(self._clients)
        if not clients:
            return
        # Fan out concurrently so one slow/stalled socket can't hold up
        # the frame cadence for everyone else.
        results = await asyncio.gather(
            *(self._send_one(ws, message) for ws in clients),
            return_exceptions=True,
        )
        for ws, result in zip(clients, results):
            if isinstance(result, Exception):
                self._clients.discard(ws)

    async def _send_one(self, ws: WebSocket, message: dict | bytes) -> None:
        if isinstance(message, bytes):
            await ws.send_bytes(message)
        else:
            await ws.send_json(message)
