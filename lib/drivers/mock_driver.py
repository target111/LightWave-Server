import logging

from lib.drivers.base import Color

logger = logging.getLogger(__name__)


class MockDriver:
    """In-memory driver for local development and tests."""

    def __init__(self, count: int):
        self.count = count
        self.brightness: float = 1.0
        self._pixels: list[Color] = [(0, 0, 0)] * count

    def set_pixel(self, index: int, color: Color) -> None:
        self._pixels[index] = color

    def set_pixels(self, colors: list[Color]) -> None:
        if len(colors) != self.count:
            raise ValueError(f"expected {self.count} colors, got {len(colors)}")
        self._pixels = list(colors)

    def fill(self, color: Color) -> None:
        self._pixels = [color] * self.count

    def show(self):
        pass

    def snapshot(self) -> list[Color]:
        return list(self._pixels)

    def close(self) -> None:
        logger.info("MockDriver closed")
