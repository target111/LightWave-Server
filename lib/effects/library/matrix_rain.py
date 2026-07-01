import random

from lib.effects import colors
from lib.effects.anim import Spawner
from lib.effects.base import Color, EffectBase, option


class MatrixRain(EffectBase):
    """
    Green 'code' drops that are guaranteed to reach the bottom of the strip.
    """

    spawn_rate: float = option(2.5, "New drops per second", min=0.0)
    trail_length: int = option(20, "Length of the drop trail", min=1)
    head_color: Color = option((180, 255, 180), "Color of the drop head")
    tail_color: Color = option((0, 255, 0), "Color of the drop trail")

    _MIN_SPEED = 10.0  # drop fall speed range in pixels/second
    _MAX_SPEED = 40.0

    def setup(self):
        self.drops: list[list[float]] = []
        self.spawner = Spawner(self.spawn_rate)

    def tick(self, dt: float):
        for _ in range(self.spawner.poll(dt)):
            speed = random.uniform(self._MIN_SPEED, self._MAX_SPEED)
            self.drops.append([0.0, speed])

        intensities: dict[int, float] = {}
        active_drops = []

        for pos, speed in self.drops:
            pos += speed * dt

            head_pixel = int(pos)

            if head_pixel - self.trail_length < self.n:
                active_drops.append([pos, speed])

                for i in range(self.trail_length):
                    pixel_index = head_pixel - i
                    if 0 <= pixel_index < self.n:
                        intensity = 1.0 - (i / self.trail_length)
                        current_val = intensities.get(pixel_index, 0.0)
                        intensities[pixel_index] = max(current_val, intensity)

        self.drops = active_drops

        for i in range(self.n):
            intensity = intensities.get(i, 0.0)
            if intensity > 0.0:
                color = self.head_color if intensity > 0.9 else self.tail_color
                self.pixels[i] = colors.scale(color, intensity)
            else:
                self.pixels[i] = (0, 0, 0)
