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
            "default": 1.0,
            "description": "Star density multiplier (1.0 = normal)",
        },
        {
            "name": "fade_time",
            "type": "float",
            "default": 0.85,
            "description": "Seconds for a star to fade in (and out again)",
        },
        {
            "name": "color",
            "type": "color",
            "default": (255, 255, 255),
            "description": "Star color",
        },
    ]

    density: float
    fade_time: float
    color: tuple[int, int, int]

    # Per-pixel spawn probability per second at density=1.0
    _BASE_SPAWN_RATE = 0.4

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
        spawn_chance = self._BASE_SPAWN_RATE * self.density * dt
        fade_step = 255 * dt / self.fade_time

        for i in range(self.led.count):
            if self.states[i] == self._OFF:
                if random.random() < spawn_chance:
                    self.states[i] = self._FADE_IN
                    self.pixel_colors[i] = self._pick_color()

            elif self.states[i] == self._FADE_IN:
                self.brightness[i] += fade_step
                if self.brightness[i] >= 255:
                    self.brightness[i] = 255
                    self.states[i] = self._FADE_OUT

            elif self.states[i] == self._FADE_OUT:
                self.brightness[i] -= fade_step
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
