from lib.drivers.base import Color


class NeoPixelDriver:
    """Real ws281x driver."""

    def __init__(self, pin_name: str, count: int):
        import board
        import neopixel

        pin = getattr(board, pin_name)
        self._pixels = neopixel.NeoPixel(pin, count, auto_write=False)
        self.count = count

    @property
    def brightness(self) -> float:
        return self._pixels.brightness

    @brightness.setter
    def brightness(self, value: float) -> None:
        self._pixels.brightness = value

    def set_pixel(self, index: int, color: Color) -> None:
        self._pixels[index] = color

    def fill(self, color: Color) -> None:
        self._pixels.fill(color)

    def show(self) -> None:
        self._pixels.show()

    def close(self) -> None:
        try:
            self._pixels.deinit()

        except Exception:
            pass
