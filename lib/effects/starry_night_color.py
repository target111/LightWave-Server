from lib.led import EffectBase
import random


class StarryNightColor(EffectBase):
    """
    Randomly fades multi-colored stars in and out smoothly.
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
            "default": 3,
            "description": "Fade speed (brightness change per frame)",
        },
    ]

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.density = float(self.config.get("density", 0.02))
        # Original 10 per frame at 20 FPS.
        # 60 FPS => 3.33. Let's use 3.
        self.fade_speed = int(self.config.get("speed", 3))

        self.palette = [
            (255, 255, 255),
            (200, 200, 255),
            (255, 240, 150),
            (255, 200, 100),
            (150, 150, 255),
            (255, 180, 220),
        ]

        self.STATE_OFF = 0
        self.STATE_IN = 1
        self.STATE_OUT = 2

        self.states = [self.STATE_OFF] * self.led.count
        self.brightness = [0] * self.led.count
        self.pixel_colors = [(0, 0, 0)] * self.led.count

    def tick(self):
        for i in range(self.led.count):
            if self.states[i] == self.STATE_OFF:
                if random.random() < (self.density / 3.0):
                    self.states[i] = self.STATE_IN
                    self.pixel_colors[i] = random.choice(self.palette)

            elif self.states[i] == self.STATE_IN:
                self.brightness[i] += self.fade_speed
                if self.brightness[i] >= 255:
                    self.brightness[i] = 255
                    self.states[i] = self.STATE_OUT

            elif self.states[i] == self.STATE_OUT:
                self.brightness[i] -= self.fade_speed
                if self.brightness[i] <= 0:
                    self.brightness[i] = 0
                    self.states[i] = self.STATE_OFF

            if self.brightness[i] > 0:
                current_color = self.pixel_colors[i]
                b_factor = self.brightness[i] / 255.0

                r = int(current_color[0] * b_factor)
                g = int(current_color[1] * b_factor)
                b = int(current_color[2] * b_factor)

                self.led.set_pixel(i, (r, g, b))
            else:
                self.led.set_pixel(i, (0, 0, 0))
