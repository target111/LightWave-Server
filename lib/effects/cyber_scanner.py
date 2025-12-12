from lib.led import EffectBase


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
            "name": "decay",
            "type": "float",
            "default": 0.97,
            "description": "Trail decay rate (0.0-1.0)",
        },
        {
            "name": "speed",
            "type": "float",
            "default": 0.55,
            "description": "Movement speed (pixels per frame)",
        },
    ]

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.eye_color = self.config.get("eye_color", (255, 0, 255))
        self.decay = float(self.config.get("decay", 0.97))
        # Original speed 0.03 (33 FPS). 1 pixel/frame. 33 px/sec.
        # 60 FPS. 33 px/sec => 0.55 px/frame.
        self.speed = float(self.config.get("speed", 0.55))

        self.heat = [0.0] * self.led.count
        self.position = 0.0
        self.direction = 1

    def tick(self):
        # Fade out
        for i in range(self.led.count):
            self.heat[i] = self.heat[i] * self.decay

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
        self.position += self.direction * self.speed

        if self.position >= self.led.count - 1:
            self.position = self.led.count - 1
            self.direction = -1
        elif self.position <= 0:
            self.position = 0
            self.direction = 1
