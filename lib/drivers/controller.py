import logging
import threading
import time
from typing import Callable, Optional

from lib.drivers.base import Color, LEDDriver

logger = logging.getLogger(__name__)


class LEDController:
    """Thread-safe facade over an LEDDriver. All hardware access goes through
    one lock so effect threads and API handlers can't trample each other."""

    def __init__(self, driver: LEDDriver):
        self._driver = driver
        self._lock = threading.Lock()
        # Called (from whichever thread mutated the state) after every
        # write. Must be cheap and thread-safe; used to fan out state to
        # websocket clients.
        self.on_change: Optional[Callable[[], None]] = None

    @property
    def count(self) -> int:
        return self._driver.count

    def _notify(self) -> None:
        cb = self.on_change
        if cb is not None:
            cb()

    def snapshot(self) -> tuple[list[Color], float]:
        """Consistent copy of the pixel buffer and brightness."""
        with self._lock:
            return self._driver.snapshot(), self._driver.brightness

    def set_pixel(self, index: int, color: Color) -> None:
        with self._lock:
            self._driver.set_pixel(index, color)
        self._notify()

    def set_pixels(self, colors: list[Color]) -> None:
        """Replace the whole frame in one lock acquisition."""
        with self._lock:
            self._driver.set_pixels(colors)
        self._notify()

    def set_color(self, color: Color) -> None:
        with self._lock:
            self._driver.fill(color)
            self._driver.show()
        self._notify()

    def set_brightness(self, brightness: float) -> None:
        with self._lock:
            self._driver.brightness = max(0.0, min(1.0, brightness))
            self._driver.show()
        self._notify()

    def show(self) -> None:
        # No notify: show() only flushes buffer writes that already
        # notified, and effects call set_pixels() + show() every frame.
        with self._lock:
            self._driver.show()

    def clear(self) -> None:
        self.set_color((0, 0, 0))

    def fade_out(self, duration: float) -> None:
        """Linearly fade brightness to 0, clear, then restore brightness.
        Blocking — call from a worker thread, not the event loop."""
        fps = 30
        steps = max(int(duration * fps), 1)
        with self._lock:
            start_brightness = self._driver.brightness

        if start_brightness <= 0:
            self.clear()
            return

        for i in range(1, steps + 1):
            self.set_brightness(start_brightness * (1.0 - i / steps))
            time.sleep(1.0 / fps)

        self.clear()
        self.set_brightness(start_brightness)

    def close(self) -> None:
        try:
            self.clear()
        finally:
            self._driver.close()
