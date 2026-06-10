import math
import time

from lib.effects.base import EffectBase


class ChristmasBreath(EffectBase):
    """
    Smoothly fades the entire strip between two colors (default Red/Green).
    """

    CONFIG_SCHEMA = [
        {
            "name": "period",
            "type": "float",
            "default": 4.0,
            "description": "Seconds for one full breath cycle",
        },
        {
            "name": "color1",
            "type": "color",
            "default": (255, 0, 0),
            "description": "First color",
        },
        {
            "name": "color2",
            "type": "color",
            "default": (0, 255, 0),
            "description": "Second color",
        },
    ]

    period: float
    color1: tuple[int, int, int]
    color2: tuple[int, int, int]

    def tick(self, dt: float):
        # Phase derives from wall-clock time, so dt is unused
        elapsed = time.time() - self.start_time.timestamp()
        phase = (math.sin(elapsed * 2 * math.pi / self.period) + 1) / 2

        r = int(self.color1[0] * phase + self.color2[0] * (1 - phase))
        g = int(self.color1[1] * phase + self.color2[1] * (1 - phase))
        b = int(self.color1[2] * phase + self.color2[2] * (1 - phase))
        self.led.set_color((r, g, b))
