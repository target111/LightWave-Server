from lib.led import EffectBase


class CandyCane(EffectBase):
    """

    Rotating Red and White stripes resembling a candy cane.

    """

    CONFIG_SCHEMA = [
        {
            "name": "speed",
            "type": "float",
            "default": 0.33,
            "description": "Rotation speed",
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

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)

        self.offset = 0.0

        self.stripe_width = int(self.config.get("stripe_width", 5))

        # Original speed 0.05 (20 FPS). Moves 1 pixel per frame. 20 px/sec.

        # New 60 FPS. Need 20 px/sec => 0.33 px/frame.

        self.speed = float(self.config.get("speed", 0.33))

        self.color1 = self.config.get("color1", (255, 0, 0))

        self.color2 = self.config.get("color2", (255, 255, 255))

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
