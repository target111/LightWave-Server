import logging
import threading
import time

from lib.drivers.base import Color, LEDDriver

logger = logging.getLogger(__name__)


class LEDController:
    """Thread-safe facade over an LEDDriver. All hardware access goes through
    one lock so effect threads and API handlers can't trample each other."""

    def __init__(self, driver: LEDDriver):
        self._driver = driver
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        return self._driver.count

    def set_pixel(self, index: int, color: Color) -> None:
        with self._lock:
            self._driver.set_pixel(index, color)

    def set_pixels(self, colors: list[Color]) -> None:
        """Replace the whole frame in one lock acquisition."""
        with self._lock:
            self._driver.set_pixels(colors)

    def set_color(self, color: Color) -> None:
        with self._lock:
            self._driver.fill(color)
            self._driver.show()

    def set_brightness(self, brightness: float) -> None:
        with self._lock:
            self._driver.brightness = max(0.0, min(1.0, brightness))
            self._driver.show()

    def show(self) -> None:
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
