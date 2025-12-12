from lib.led import EffectBase
import math


class Aurora(EffectBase):
    """
    Smooth, flowing waves of Green, Blue and Purple (Northern Lights).
    """

    CONFIG_SCHEMA = [
        {
            "name": "speed",
            "type": "float",
            "default": 0.04,
            "description": "Animation speed",
        }
    ]

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.t = 0.0
        self.speed = float(self.config.get("speed", 0.04))  # Adjusted for 60 FPS

    def tick(self):
        self.t += self.speed

        for i in range(self.led.count):
            wave1 = math.sin(i * 0.1 + self.t)
            wave2 = math.sin(i * 0.05 - self.t * 0.5)
            combined = wave1 + wave2

            r = int((math.sin(combined) + 1) * 30)
            g = int((math.sin(combined + 2) + 1) * 100)
            b = int((math.sin(combined + 4) + 1) * 100)

            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            self.led.set_pixel(i, (r, g, b))
