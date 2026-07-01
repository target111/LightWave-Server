import random

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

    # The simulation was tuned at ~30 FPS and is step-sensitive, so run
    # the loop at that rate instead of scaling the math per tick.
    TARGET_FPS = 33

    _BASE_COOLING = 55  # heat units shed per update at cooling=1.0
    _PALETTE = Gradient(
        (0, 0, 0), (255, 0, 0), (255, 255, 0), (255, 255, 255)
    )

    def setup(self):
        self.heat = [0] * self.n

    def tick(self, dt: float):
        # Step 1: Cool down
        cooling = int(self._BASE_COOLING * self.cooling)
        max_cooldown = ((cooling * 10) // self.n) + 2
        for i in range(self.n):
            cooldown = random.randint(0, max_cooldown)
            self.heat[i] = max(0, self.heat[i] - cooldown)

        # Step 2: Drift
        for i in range(self.n - 1, 1, -1):
            self.heat[i] = (
                self.heat[i - 1] + self.heat[i - 2] + self.heat[i - 2]
            ) // 3

        # Step 3: Spark
        if random.random() < self.sparking:
            y = random.randint(0, 7)
            self.heat[y] = min(255, self.heat[y] + random.randint(160, 255))

        # Step 4: Map to color
        for i in range(self.n):
            self.pixels[i] = self._PALETTE.sample(self.heat[i] / 255)
