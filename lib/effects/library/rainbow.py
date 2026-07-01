from lib.effects import colors
from lib.effects.anim import wrap
from lib.effects.base import EffectBase, option


class RainbowCycle(EffectBase):
    """
    Draw rainbow that uniformly distributes itself across all pixels.
    """

    speed: float = option(
        1.0, "Speed multiplier (1.0 = one cycle per ~4.3 s)", min=0.0
    )

    _BASE_SPEED = 60.0  # color-wheel steps (of 256)/second at speed=1.0

    def setup(self):
        self.pos = 0.0

    def tick(self, dt: float):
        self.pos = wrap(self.pos + self._BASE_SPEED * self.speed * dt, 256)

        j = int(self.pos)
        for i in range(self.n):
            self.pixels[i] = colors.wheel(i * 256 // self.n + j)
