import random

from lib.effects.base import EffectBase


class StarryNight(EffectBase):
    """
    Randomly fades stars in and out smoothly.
    """

    CONFIG_SCHEMA = [
        {
            "name": "density",
            "type": "float",
            "default": 0.02,
            "description": "Density of stars (probability per frame)",
        },
        {
            "name": "speed",
            "type": "int",
            # Original fade was 15/frame at 20 FPS; 5/frame at 60 FPS.
            "default": 5,
            "description": "Fade speed (brightness change per frame)",
        },
        {
            "name": "color",
            "type": "color",
            "default": (255, 255, 255),
            "description": "Star color",
        },
    ]

    density: float
    speed: int
    color: tuple[int, int, int]

    _OFF, _FADE_IN, _FADE_OUT = range(3)

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.states = [self._OFF] * self.led.count
        self.brightness = [0.0] * self.led.count
        self.pixel_colors: list[tuple[int, int, int]] = [
            (0, 0, 0)
        ] * self.led.count

    def _pick_color(self) -> tuple[int, int, int]:
        """Color for a newly spawned star. Subclasses can override."""
        return self.color

    def tick(self, dt: float):
        frames = dt * self.TARGET_FPS

        for i in range(self.led.count):
            if self.states[i] == self._OFF:
                # Density was tuned per-frame at 20 FPS; divide by 3 so the
                # 60 FPS loop spawns at the same rate per second.
                if random.random() < (self.density / 3.0) * frames:
                    self.states[i] = self._FADE_IN
                    self.pixel_colors[i] = self._pick_color()

            elif self.states[i] == self._FADE_IN:
                self.brightness[i] += self.speed * frames
                if self.brightness[i] >= 255:
                    self.brightness[i] = 255
                    self.states[i] = self._FADE_OUT

            elif self.states[i] == self._FADE_OUT:
                self.brightness[i] -= self.speed * frames
                if self.brightness[i] <= 0:
                    self.brightness[i] = 0
                    self.states[i] = self._OFF

            if self.brightness[i] > 0:
                star = self.pixel_colors[i]
                b_factor = self.brightness[i] / 255.0
                r = int(star[0] * b_factor)
                g = int(star[1] * b_factor)
                b = int(star[2] * b_factor)
                self.led.set_pixel(i, (r, g, b))
            else:
                self.led.set_pixel(i, (0, 0, 0))
