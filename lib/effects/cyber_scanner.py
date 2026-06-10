from lib.effects.base import EffectBase


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
            # Original speed was 1 px/frame at 33 FPS (33 px/sec);
            # at 60 FPS that is 0.55 px/frame.
            "default": 0.55,
            "description": "Movement speed (pixels per frame)",
        },
    ]

    eye_color: tuple[int, int, int]
    decay: float
    speed: float

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.heat = [0.0] * self.led.count
        self.position = 0.0
        self.direction = 1

    def tick(self, dt: float):
        frames = dt * self.TARGET_FPS

        # Fade out
        decay = self.decay**frames
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
        self.position += self.direction * self.speed * frames

        if self.position >= self.led.count - 1:
            self.position = self.led.count - 1
            self.direction = -1
        elif self.position <= 0:
            self.position = 0
            self.direction = 1
