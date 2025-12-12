from lib.led import EffectBase


class RainbowCycle(EffectBase):
    """
    Draw rainbow that uniformly distributes itself across all pixels on the strip.
    """

    CONFIG_SCHEMA = [
        {"name": "speed", "type": "float", "default": 1.0, "description": "Cycle speed"}
    ]

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.pos = 0
        self.speed = float(self.config.get("speed", 1.0))

    def wheel(self, pos):
        pos = int(pos)
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)

    def tick(self):
        # Increment position
        self.pos += self.speed
        if self.pos >= 256:
            self.pos -= 256

        j = int(self.pos)
        for i in range(self.led.count):
            pixel_index = (i * 256 // self.led.count) + j
            self.led.set_pixel(i, self.wheel(pixel_index & 255))
