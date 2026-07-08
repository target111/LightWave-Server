import random

from lib.effects import colors
from lib.effects.base import Color, EffectBase, option


class StarryNight(EffectBase):
    """
    Randomly fades stars in and out smoothly.
    """

    PALETTE: list[Color] = [
        (255, 255, 255),
        (200, 200, 255),
        (255, 240, 150),
        (255, 200, 100),
        (150, 150, 255),
        (255, 180, 220),
    ]

    density: float = option(
        1.0, "Star density multiplier (1.0 = normal)", min=0.0
    )
    fade_time: float = option(
        1.4, "Seconds for a star to fade in (and out again)", min=0.01
    )
    colorful: bool = option(
        True, "Multi-colored stars; false uses a single color"
    )
    color: Color = option((255, 255, 255), "Star color when colorful is off")
    saturation: float = option(
        1.0,
        "Saturation multiplier for colorful stars (0 = white, >1 = more vivid)",
        min=0.0,
    )
    hue_shift: float = option(
        0.0, "Degrees to rotate colorful star hues (0-360)"
    )

    # Per-pixel spawn probability per second at density=1.0
    _BASE_SPAWN_RATE = 0.4

    _OFF, _FADE_IN, _FADE_OUT = range(3)

    def setup(self):
        self.states = [self._OFF] * self.n
        self.brightness = [0.0] * self.n
        self.pixel_colors: list[Color] = [(0, 0, 0)] * self.n
        # Skip the HSV round-trip (and its rounding) when the palette is
        # used as-is, so the default output matches the curated colors.
        if self.saturation == 1.0 and self.hue_shift == 0.0:
            self.palette = list(self.PALETTE)
        else:
            self.palette = [
                colors.adjust_hsv(
                    c,
                    hue_shift=self.hue_shift / 360.0,
                    saturation=self.saturation,
                )
                for c in self.PALETTE
            ]

    def _pick_color(self) -> Color:
        """Color for a newly spawned star."""
        if self.colorful:
            return random.choice(self.palette)
        return self.color

    def tick(self, dt: float):
        spawn_chance = self._BASE_SPAWN_RATE * self.density * dt
        fade_step = 255 * dt / self.fade_time

        for i in range(self.n):
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
                b_factor = self.brightness[i] / 255.0
                self.pixels[i] = colors.scale(self.pixel_colors[i], b_factor)
            else:
                self.pixels[i] = (0, 0, 0)
