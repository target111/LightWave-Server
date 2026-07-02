import asyncio
import contextlib
import logging
from typing import Optional

from fastapi import WebSocket

from lib.services.effect import EffectService

logger = logging.getLogger(__name__)


class FrameBroadcaster:
    """Fans out LED state to websocket clients.

    Effect threads and API handlers call `notify()` (cheap and
    thread-safe) via `LEDController.on_change`; an asyncio task coalesces
    those wake-ups, snapshots the controller, and pushes one frame to
    every client, throttled to `FPS`.

    Wire protocol: pixel frames are binary — one brightness byte
    (0-255) followed by 3 bytes (RGB) per LED. The running preset is
    sent as a JSON text message, only on connect and when it changes."""

    FPS = 30

    def __init__(self, service: EffectService):
        self._service = service
        self._clients: set[WebSocket] = set()
        self._dirty = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Begin broadcasting. Must be called from the running event loop."""
        self._loop = asyncio.get_running_loop()
        self._task = self._loop.create_task(self._run())
        self._service.controller.on_change = self.notify

    async def stop(self) -> None:
        self._service.controller.on_change = None
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

    def _running_name(self) -> Optional[str]:
        running = self._service.running
        if running is not None and running.is_alive():
            return running.__class__.__name__
        return None

    def _status(self) -> dict:
        return {"type": "status", "running": self._running_name()}

    def _frame(self) -> bytes:
        pixels, brightness = self._service.controller.snapshot()
        frame = bytearray(1 + 3 * len(pixels))
        frame[0] = max(0, min(255, round(brightness * 255)))
        i = 1
        for r, g, b in pixels:
            frame[i] = max(0, min(255, r))
            frame[i + 1] = max(0, min(255, g))
            frame[i + 2] = max(0, min(255, b))
            i += 3
        return bytes(frame)

    async def _run(self) -> None:
        frame_time = 1.0 / self.FPS
        last_running = self._running_name()
        while True:
            try:
                await asyncio.wait_for(self._dirty.wait(), timeout=1.0)
                dirty = True
            except TimeoutError:
                # No pixel writes — but an effect may still have finished
                # or crashed without touching the strip, so fall through
                # to the status check below.
                dirty = False
            self._dirty.clear()

            running = self._running_name()
            if running != last_running:
                last_running = running
                await self._send_all(self._status())
            if dirty and self._clients:
                await self._send_all(self._frame())
            if dirty:
                await asyncio.sleep(frame_time)

    async def _send_all(self, message: dict | bytes) -> None:
        dead = []
        for ws in self._clients:
            try:
                if isinstance(message, bytes):
                    await ws.send_bytes(message)
                else:
                    await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
