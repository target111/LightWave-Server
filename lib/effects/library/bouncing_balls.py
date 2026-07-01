from lib.effects.base import EffectBase, option


class BouncingBalls(EffectBase):
    """
    Simulates multi-colored balls bouncing under gravity.
    """

    ball_count: int = option(3, "Number of balls", min=1)
    gravity: float = option(
        1.0, "Gravity strength multiplier (1.0 = normal)", min=0.0
    )
    dampening: float = option(
        0.90, "Bounce dampening (0.0-1.0)", min=0.0, max=1.0
    )

    _BASE_GRAVITY = -5.81  # strip-heights/second² at gravity=1.0

    def setup(self):
        self._g = self._BASE_GRAVITY * self.gravity
        self.start_height = 1
        self.colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]

        # Seconds since each ball's current arc started; negative values
        # stagger the initial drops
        self.elapsed = [-(i * 0.5) for i in range(self.ball_count)]
        self.velocities = [0.0] * self.ball_count
        self.heights = [self.start_height] * self.ball_count

    def tick(self, dt: float):
        self.clear()

        for i in range(self.ball_count):
            self.elapsed[i] += dt
            t = self.elapsed[i]
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

                self.elapsed[i] = 0.0
                self.heights[i] = 0
                self.velocities[i] = new_v

                if new_v < 1.0:
                    self.heights[i] = self.start_height
                    self.velocities[i] = 0
                    self.elapsed[i] = -1.0

            position = int(h * (self.n - 1))

            if 0 <= position < self.n:
                self.pixels[position] = self.colors[i % len(self.colors)]
