import math

from lib.effects import colors
from lib.effects.base import Color, EffectBase, option


class ChristmasBreath(EffectBase):
    """
    Smoothly fades the entire strip between two colors (default Red/Green).
    """

    period: float = option(4.0, "Seconds for one full breath cycle", min=0.1)
    color1: Color = option((255, 0, 0), "First color")
    color2: Color = option((0, 255, 0), "Second color")

    def setup(self):
        self.elapsed = 0.0

    def tick(self, dt: float):
        self.elapsed += dt
        phase = (math.sin(self.elapsed * 2 * math.pi / self.period) + 1) / 2
        self.fill(colors.lerp(self.color2, self.color1, phase))
