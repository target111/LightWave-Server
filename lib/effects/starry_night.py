from lib.led import EffectBase
import random


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

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.density = float(self.config.get("density", 0.02))
        # Original 15 per frame at 20 FPS (0.05s).
        # At 60 FPS, we need 1/3rd speed => 5.
        self.fade_speed = int(self.config.get("speed", 5))

        self.STATE_OFF = 0
        self.STATE_IN = 1
        self.STATE_OUT = 2

        self.states = [self.STATE_OFF] * self.led.count
        self.brightness = [0] * self.led.count
        self.color = self.config.get("color", (255, 255, 255))

    def tick(self):
        for i in range(self.led.count):
            if self.states[i] == self.STATE_OFF:
                if random.random() < (
                    self.density / 3.0
                ):  # Adjust density for higher FPS check rate
                    self.states[i] = self.STATE_IN

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
                b_factor = self.brightness[i] / 255.0
                r = int(self.color[0] * b_factor)
                g = int(self.color[1] * b_factor)
                b = int(self.color[2] * b_factor)
                self.led.set_pixel(i, (r, g, b))
            else:
                self.led.set_pixel(i, (0, 0, 0))
