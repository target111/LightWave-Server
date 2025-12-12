from lib.led import EffectBase
import random


class Fire(EffectBase):
    """
    Simulates fire rising up the LED strip.
    """

    CONFIG_SCHEMA = [
        {
            "name": "cooling",
            "type": "int",
            "default": 55,
            "description": "Rate at which cells cool down",
        },
        {
            "name": "sparking",
            "type": "int",
            "default": 120,
            "description": "Chance of a spark igniting (0-255)",
        },
    ]

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.cooling = int(self.config.get("cooling", 55))
        self.sparking = int(self.config.get("sparking", 120))
        self.heat = [0] * self.led.count

        self.palette = []
        for i in range(256):
            if i < 85:
                self.palette.append((i * 3, 0, 0))
            elif i < 170:
                self.palette.append((255, (i - 85) * 3, 0))
            else:
                self.palette.append((255, 255, (i - 170) * 3))

        # To maintain original speed (~30 FPS) on 60 FPS loop
        self.accum = 0.0
        self.update_interval = 0.03

    def tick(self):
        # We can either skip frames or scale logic.
        # Fire simulation is sensitive to steps. Skipping frames is safer for look.
        self.accum += 1.0 / 60.0  # Assuming 60 FPS from EffectBase
        if self.accum < self.update_interval:
            # Just redraw existing heat? Or do nothing?
            # EffectBase calls show(). If we do nothing, it shows same frame.
            # But we need to render heat to pixels every frame if we want smooth?
            # No, if heat doesn't change, pixels don't change.
            return

        self.accum -= self.update_interval

        # Step 1: Cool down
        for i in range(self.led.count):
            cooldown = random.randint(0, ((self.cooling * 10) // self.led.count) + 2)
            self.heat[i] = max(0, self.heat[i] - cooldown)

        # Step 2: Drift
        for i in range(self.led.count - 1, 1, -1):
            self.heat[i] = (self.heat[i - 1] + self.heat[i - 2] + self.heat[i - 2]) // 3

        # Step 3: Spark
        if random.randint(0, 255) < self.sparking:
            y = random.randint(0, 7)
            self.heat[y] = min(255, self.heat[y] + random.randint(160, 255))

        # Step 4: Map to color
        for i in range(self.led.count):
            color_index = self.heat[i]
            if color_index >= 256:
                color_index = 255
            self.led.set_pixel(i, self.palette[color_index])
