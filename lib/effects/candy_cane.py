from lib.effects.base import EffectBase


class CandyCane(EffectBase):
    """
    Rotating Red and White stripes resembling a candy cane.
    """

    CONFIG_SCHEMA = [
        {
            "name": "speed",
            "type": "float",
            # Original speed was 1 px/frame at 20 FPS (20 px/sec);
            # at 60 FPS that is 0.33 px/frame.
            "default": 0.33,
            "description": "Rotation speed (pixels per frame)",
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

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.offset = 0.0

    def tick(self):
        current_offset = int(self.offset)

        for i in range(self.led.count):
            if ((i + current_offset) // self.stripe_width) % 2 == 0:
                self.led.set_pixel(i, self.color1)
            else:
                self.led.set_pixel(i, self.color2)

        self.offset += self.speed

        if self.offset >= (self.stripe_width * 2):
            self.offset -= self.stripe_width * 2
