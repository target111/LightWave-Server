import time

from lib.effects.base import EffectBase


class BouncingBalls(EffectBase):
    """
    Simulates multi-colored balls bouncing under gravity.
    """

    CONFIG_SCHEMA = [
        {
            "name": "ball_count",
            "type": "int",
            "default": 3,
            "description": "Number of balls",
        },
        {
            "name": "gravity",
            "type": "float",
            "default": 1.0,
            "description": "Gravity strength multiplier (1.0 = normal)",
        },
        {
            "name": "dampening",
            "type": "float",
            "default": 0.90,
            "description": "Bounce dampening (0.0-1.0)",
        },
    ]

    ball_count: int
    gravity: float
    dampening: float

    _BASE_GRAVITY = -5.81  # strip-heights/second² at gravity=1.0

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self._g = self._BASE_GRAVITY * self.gravity
        self.start_height = 1
        self.colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]

        self.start_times = [0.0] * self.ball_count
        self.velocities = [0.0] * self.ball_count
        self.heights = [self.start_height] * self.ball_count

        now = time.time()
        for i in range(self.ball_count):
            self.start_times[i] = now + (i * 0.5)
            self.velocities[i] = 0.0

    def tick(self, dt: float):
        # Physics integrate against wall-clock time, so dt is unused
        now = time.time()
        self.led.clear()

        for i in range(self.ball_count):
            t = now - self.start_times[i]
            if t < 0:
                continue

            h = (
                0.5 * self._g * pow(t, 2)
                + self.velocities[i] * t
                + self.heights[i]
            )

            if h < 0:
                h = 0
                v_impact = self.velocities[i] + self._g * t
                new_v = -v_impact * self.dampening

                self.start_times[i] = now
                self.heights[i] = 0
                self.velocities[i] = new_v

                if new_v < 1.0:
                    self.heights[i] = self.start_height
                    self.velocities[i] = 0
                    self.start_times[i] = now + 1.0

            position = int(h * (self.led.count - 1))

            if 0 <= position < self.led.count:
                self.led.set_pixel(position, self.colors[i % len(self.colors)])
