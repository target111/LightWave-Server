import math

from lib.effects.base import EffectBase, option


class Aurora(EffectBase):
    """
    Smooth, flowing waves of Green, Blue and Purple (Northern Lights).
    """

    speed: float = option(1.0, "Speed multiplier (1.0 = normal)", min=0.0)

    _BASE_SPEED = 2.4  # wave phase advance in radians/second at speed=1.0

    def setup(self):
        self.t = 0.0

    def tick(self, dt: float):
        self.t += self._BASE_SPEED * self.speed * dt

        for i in range(self.n):
            wave1 = math.sin(i * 0.1 + self.t)
            wave2 = math.sin(i * 0.05 - self.t * 0.5)
            combined = wave1 + wave2

            r = int((math.sin(combined) + 1) * 30)
            g = int((math.sin(combined + 2) + 1) * 100)
            b = int((math.sin(combined + 4) + 1) * 100)

            self.pixels[i] = (r, g, b)
