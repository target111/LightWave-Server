import logging
import threading
from typing import Callable

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
        self.on_change: Callable[[], None] | None = None

    @property
    def count(self) -> int:
        return self._driver.count

    @property
    def brightness(self) -> float:
        with self._lock:
            return self._driver.brightness

    def _notify(self) -> None:
        cb = self.on_change
        if cb is not None:
            cb()

    def snapshot(self) -> tuple[list[Color], float]:
        """Consistent copy of the pixel buffer and brightness."""
        with self._lock:
            return self._driver.snapshot(), self._driver.brightness

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

    def close(self) -> None:
        try:
            self.clear()
        finally:
            self._driver.close()
