import asyncio
import contextlib
import logging
from itertools import chain
from typing import Optional

from fastapi import WebSocket

from lib.services.effect import EffectService

logger = logging.getLogger(__name__)


class FrameBroadcaster:
    """Fans out LED state to websocket clients.

    Effect threads and API handlers call `notify()` (cheap and
    thread-safe) via `LEDController.on_change` (pixel writes) and
    `EffectService.on_state_change` (preset started/stopped/died); an
    asyncio task coalesces those wake-ups, snapshots the controller, and
    pushes one frame to every client, throttled to `fps`.

    Wire protocol: pixel frames are binary — one brightness byte
    (0-255) followed by 3 bytes (RGB) per LED. The running preset is
    sent as a JSON text message, only on connect and when it changes."""

    def __init__(self, service: EffectService, fps: int = 30):
        self._service = service
        self._fps = fps
        self._clients: set[WebSocket] = set()
        self._dirty = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Begin broadcasting. Must be called from the running event loop."""
        self._loop = asyncio.get_running_loop()
        self._task = self._loop.create_task(self._run())
        self._service.controller.on_change = self.notify
        self._service.on_state_change = self.notify

    async def stop(self) -> None:
        self._service.controller.on_change = None
        self._service.on_state_change = None
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
        return {"type": "status", "running": self._service.running_name}

    def _frame(self) -> bytes:
        pixels, brightness = self._service.controller.snapshot()
        return bytes([round(brightness * 255), *chain.from_iterable(pixels)])

    async def _run(self) -> None:
        frame_time = 1.0 / self._fps
        last_running = self._service.running_name
        while True:
            await self._dirty.wait()
            self._dirty.clear()

            try:
                running = self._service.running_name
                if running != last_running:
                    last_running = running
                    await self._send_all(self._status())
                if self._clients:
                    await self._send_all(self._frame())
            except asyncio.CancelledError:
                raise
            except Exception:
                # A bad frame must not kill broadcasting for everyone.
                logger.exception("frame broadcast failed")
            await asyncio.sleep(frame_time)

    async def _send_all(self, message: dict | bytes) -> None:
        dead = []
        # Snapshot: each send awaits, and a client connecting or
        # disconnecting meanwhile would mutate the set mid-iteration.
        for ws in tuple(self._clients):
            try:
                if isinstance(message, bytes):
                    await ws.send_bytes(message)
                else:
                    await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
