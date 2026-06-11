from lib.effects.base import EffectBase, fade_factor


class CyberScanner(EffectBase):
    """
    A moving 'eye' that leaves a fading trail behind it.
    """

    CONFIG_SCHEMA = [
        {
            "name": "eye_color",
            "type": "color",
            "default": (255, 0, 255),
            "description": "Color of the eye",
        },
        {
            "name": "trail_fade",
            "type": "float",
            "default": 1.6,
            "description": "Seconds for the trail to fade out",
        },
        {
            "name": "speed",
            "type": "float",
            "default": 1.0,
            "description": "Speed multiplier (1.0 = 33 pixels/second)",
        },
    ]

    eye_color: tuple[int, int, int]
    trail_fade: float
    speed: float

    _BASE_SPEED = 33.0  # pixels/second at speed=1.0

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.heat = [0.0] * self.led.count
        self.position = 0.0
        self.direction = 1

    def tick(self, dt: float):
        # Fade out
        decay = fade_factor(dt, self.trail_fade)
        for i in range(self.led.count):
            self.heat[i] = self.heat[i] * decay

        # Set head
        pos_idx = int(self.position)
        if 0 <= pos_idx < self.led.count:
            self.heat[pos_idx] = 1.0

        # Render
        for i in range(self.led.count):
            pixel_r = int(self.eye_color[0] * self.heat[i])
            pixel_g = int(self.eye_color[1] * self.heat[i])
            pixel_b = int(self.eye_color[2] * self.heat[i])
            self.led.set_pixel(i, (pixel_r, pixel_g, pixel_b))

        # Move
        self.position += self.direction * self._BASE_SPEED * self.speed * dt

        if self.position >= self.led.count - 1:
            self.position = self.led.count - 1
            self.direction = -1
        elif self.position <= 0:
            self.position = 0
            self.direction = 1
