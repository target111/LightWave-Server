from lib.effects.base import EffectBase


class CandyCane(EffectBase):
    """
    Rotating Red and White stripes resembling a candy cane.
    """

    CONFIG_SCHEMA = [
        {
            "name": "speed",
            "type": "float",
            "default": 1.0,
            "description": "Speed multiplier (1.0 = 20 pixels/second)",
        },
        {
            "name": "stripe_width",
            "type": "int",
            "default": 5,
            "description": "Width of each stripe in pixels",
        },
        {
            "name": "color1",
            "type": "color",
            "default": (255, 0, 0),
            "description": "First stripe color",
        },
        {
            "name": "color2",
            "type": "color",
            "default": (255, 255, 255),
            "description": "Second stripe color",
        },
    ]

    speed: float
    stripe_width: int
    color1: tuple[int, int, int]
    color2: tuple[int, int, int]

    _BASE_SPEED = 20.0  # pixels/second at speed=1.0

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.offset = 0.0

    def tick(self, dt: float):
        current_offset = int(self.offset)

        for i in range(self.led.count):
            if ((i + current_offset) // self.stripe_width) % 2 == 0:
                self.led.set_pixel(i, self.color1)
            else:
                self.led.set_pixel(i, self.color2)

        self.offset += self._BASE_SPEED * self.speed * dt

        if self.offset >= (self.stripe_width * 2):
            self.offset -= self.stripe_width * 2
