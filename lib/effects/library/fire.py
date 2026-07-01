import random

from lib.effects import colors
from lib.effects.base import EffectBase, option
from lib.effects.colors import Gradient


class Fire(EffectBase):
    """
    Simulates fire rising up the LED strip.
    """

    cooling: float = option(
        1.0, "Cooling rate multiplier (higher = shorter flames)", min=0.0
    )
    sparking: float = option(
        0.47,
        "Chance of a spark igniting per update (0.0-1.0)",
        min=0.0,
        max=1.0,
    )
    hue_shift: float = option(
        0.0,
        "Degrees to rotate the flame colors (0-360; 240 = blue fire)",
    )

    # The simulation was tuned at ~30 FPS and is step-sensitive, so run
    # the loop at that rate instead of scaling the math per tick.
    TARGET_FPS = 33

    _BASE_COOLING = 55  # heat units shed per update at cooling=1.0
    # Cold to hot; black and the white-hot core are unaffected by
    # hue_shift (they carry no hue)
    _PALETTE_STOPS = ((255, 0, 0), (255, 255, 0), (255, 255, 255))

    def setup(self):
        self.heat = [0.0] * self.n
        # Skip the HSV round-trip (and its rounding) at hue_shift=0 so
        # the default flame matches the classic palette exactly.
        stops = self._PALETTE_STOPS
        if self.hue_shift != 0.0:
            stops = tuple(
                colors.adjust_hsv(c, hue_shift=self.hue_shift / 360.0)
                for c in stops
            )
        self.palette = Gradient((0, 0, 0), *stops)

    def tick(self, dt: float):
        # Step 1: Cool down. The multiplier is applied after the integer
        # base term, keeping the knob continuous: quantizing it through
        # int()/floor-division gave it dead zones and cliffs on long
        # strips (at 300 LEDs the whole 0.5-0.545 range collapsed to one
        # value). The base term matches the classic tuning at cooling=1.
        max_cooldown = self.cooling * (
            (self._BASE_COOLING * 10) // self.n + 2
        )
        for i in range(self.n):
            self.heat[i] = max(
                0.0, self.heat[i] - random.uniform(0.0, max_cooldown)
            )

        # Step 2: Drift. Floor division is deliberate: the truncation is
        # part of the classic decay (it sheds ~1/3 heat unit per step).
        for i in range(self.n - 1, 1, -1):
            self.heat[i] = (
                self.heat[i - 1] + 2.0 * self.heat[i - 2]
            ) // 3

        # Step 3: Spark
        if random.random() < self.sparking:
            y = random.randint(0, 7)
            self.heat[y] = min(
                255.0, self.heat[y] + random.uniform(160.0, 255.0)
            )

        # Step 4: Map to color
        for i in range(self.n):
            self.pixels[i] = self.palette.sample(self.heat[i] / 255)
