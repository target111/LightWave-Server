import math

from lib.effects import colors
from lib.effects.base import Color, EffectBase, option


class BouncingBalls(EffectBase):
    """
    Simulates multi-colored balls bouncing under gravity.
    """

    ball_count: int = option(3, "Number of balls", min=1)
    gravity: float = option(
        1.0, "Gravity strength multiplier (1.0 = normal)", min=0.0
    )
    dampening: float = option(
        0.90, "Bounce dampening (0.0-1.0, 1.0 = bounces forever)",
        min=0.0,
        max=1.0,
    )

    _BASE_GRAVITY = -5.81  # strip-heights/second² at gravity=1.0
    # Rebounds that would peak below this height (in strip-heights) end
    # the bounce cycle: the ball rests a second, then drops again
    _MIN_BOUNCE_HEIGHT = 0.086

    def setup(self):
        self._g = self._BASE_GRAVITY * self.gravity
        self.start_height = 1
        # Rebound speed that peaks exactly at _MIN_BOUNCE_HEIGHT; scales
        # with gravity so the animation loops the same at any setting
        self._min_bounce_v = math.sqrt(2.0 * -self._g * self._MIN_BOUNCE_HEIGHT)
        # Hues spread evenly around the color wheel, so every ball is
        # distinct at any ball_count
        self.colors = [
            colors.wheel(i * 256 // self.ball_count)
            for i in range(self.ball_count)
        ]

        # Seconds since each ball's current arc started; negative values
        # stagger the initial drops
        self.elapsed = [-(i * 0.5) for i in range(self.ball_count)]
        self.velocities = [0.0] * self.ball_count
        self.heights = [self.start_height] * self.ball_count

    def _draw(self, idx: int, color: Color, weight: float):
        """Blend a weighted dot into the frame (max, so balls overlap)."""
        if not (0 <= idx < self.n) or weight <= 0.0:
            return
        r, g, b = colors.scale(color, weight)
        pr, pg, pb = self.pixels[idx]
        self.pixels[idx] = (max(pr, r), max(pg, g), max(pb, b))

    def tick(self, dt: float):
        self.clear()

        for i in range(self.ball_count):
            self.elapsed[i] += dt
            t = self.elapsed[i]
            if t < 0:
                continue

            h = (
                0.5 * self._g * t * t
                + self.velocities[i] * t
                + self.heights[i]
            )

            while h < 0:
                # The floor was crossed mid-frame: solve the arc for the
                # exact impact, rebound there, and replay the rest of the
                # frame on the new arc. Impact speed via energy
                # conservation: v² = v0² - 2·g·h0.
                v0 = self.velocities[i]
                v_impact = math.sqrt(
                    v0 * v0 - 2.0 * self._g * self.heights[i]
                )
                new_v = v_impact * self.dampening

                if new_v < self._min_bounce_v:
                    # Too slow to bounce visibly: rest at the floor for a
                    # second, then drop from the top again
                    self.heights[i] = self.start_height
                    self.velocities[i] = 0.0
                    self.elapsed[i] = -1.0
                    h = 0.0
                    break

                t_impact = (v0 + v_impact) / -self._g
                t = max(0.0, t - t_impact)
                self.elapsed[i] = t
                self.heights[i] = 0.0
                self.velocities[i] = new_v
                h = 0.5 * self._g * t * t + new_v * t

            # Anti-aliased dot: brightness split across the two pixels
            # the ball overlaps, so motion stays smooth near arc peaks
            pos = h * (self.n - 1)
            idx = int(pos)
            frac = pos - idx
            self._draw(idx, self.colors[i], 1.0 - frac)
            self._draw(idx + 1, self.colors[i], frac)
