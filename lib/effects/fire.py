import random

from lib.effects.base import EffectBase


class Fire(EffectBase):
    """
    Simulates fire rising up the LED strip.
    """

    CONFIG_SCHEMA = [
        {
            "name": "cooling",
            "type": "float",
            "default": 1.0,
            "description": "Cooling rate multiplier (higher = shorter flames)",
        },
        {
            "name": "sparking",
            "type": "float",
            "default": 0.47,
            "description": "Chance of a spark igniting per update (0.0-1.0)",
        },
    ]

    cooling: float
    sparking: float

    _BASE_COOLING = 55  # heat units shed per update at cooling=1.0

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.heat = [0] * self.led.count

        self.palette = []
        for i in range(256):
            if i < 85:
                self.palette.append((i * 3, 0, 0))
            elif i < 170:
                self.palette.append((255, (i - 85) * 3, 0))
            else:
                self.palette.append((255, 255, (i - 170) * 3))

        # The simulation was tuned at ~30 FPS and is step-sensitive, so on
        # the 60 FPS loop we skip frames instead of scaling the math.
        self.accum = 0.0
        self.update_interval = 0.03

    def tick(self, dt: float):
        self.accum += dt
        if self.accum < self.update_interval:
            return

        self.accum -= self.update_interval

        # Step 1: Cool down
        cooling = int(self._BASE_COOLING * self.cooling)
        max_cooldown = ((cooling * 10) // self.led.count) + 2
        for i in range(self.led.count):
            cooldown = random.randint(0, max_cooldown)
            self.heat[i] = max(0, self.heat[i] - cooldown)

        # Step 2: Drift
        for i in range(self.led.count - 1, 1, -1):
            self.heat[i] = (
                self.heat[i - 1] + self.heat[i - 2] + self.heat[i - 2]
            ) // 3

        # Step 3: Spark
        if random.random() < self.sparking:
            y = random.randint(0, 7)
            self.heat[y] = min(255, self.heat[y] + random.randint(160, 255))

        # Step 4: Map to color
        for i in range(self.led.count):
            color_index = min(self.heat[i], 255)
            self.led.set_pixel(i, self.palette[color_index])
