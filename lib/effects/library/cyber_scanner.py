from lib.effects import colors
from lib.effects.anim import FadeBuffer
from lib.effects.base import Color, EffectBase, option


class CyberScanner(EffectBase):
    """
    A moving 'eye' that leaves a fading trail behind it.
    """

    eye_color: Color = option((255, 0, 255), "Color of the eye")
    trail_fade: float = option(
        1.6, "Seconds for the trail to fade out", min=0.0
    )
    speed: float = option(
        1.0, "Speed multiplier (1.0 = 33 pixels/second)", min=0.0
    )

    _BASE_SPEED = 33.0  # pixels/second at speed=1.0

    def setup(self):
        self.trail = FadeBuffer(self.n, self.trail_fade)
        self.position = 0.0
        self.direction = 1

    def tick(self, dt: float):
        self.trail.decay(dt)

        # Set head
        pos_idx = int(self.position)
        if 0 <= pos_idx < self.n:
            self.trail[pos_idx] = 1.0

        # Render
        for i, heat in enumerate(self.trail):
            self.pixels[i] = colors.scale(self.eye_color, heat)

        # Move
        self.position += self.direction * self._BASE_SPEED * self.speed * dt

        if self.position >= self.n - 1:
            self.position = self.n - 1
            self.direction = -1
        elif self.position <= 0:
            self.position = 0
            self.direction = 1
