from lib.effects import colors
from lib.effects.anim import FadeBuffer, wrap
from lib.effects.base import Color, EffectBase, option


class CyberScanner(EffectBase):
    """
    A moving 'eye' that leaves a fading trail behind it, slowly rotating
    through colors. The trail keeps the hue it was painted with.
    """

    eye_color: Color = option((255, 0, 255), "Base color of the eye")
    trail_fade: float = option(
        1.6, "Seconds for the trail to fade out", min=0.0
    )
    speed: float = option(
        1.0, "Speed multiplier (1.0 = 33 pixels/second)", min=0.0
    )
    hue_cycle: float = option(
        40.0,
        "Degrees/second to rotate the eye hue (0 = static color)",
        min=0.0,
    )
    saturation: float = option(
        1.0,
        "Color saturation (0 = white/chrome, 1 = vivid)",
        min=0.0,
        max=1.0,
    )

    _BASE_SPEED = 33.0  # pixels/second at speed=1.0

    def setup(self):
        self.trail = FadeBuffer(self.n, self.trail_fade)
        self.trail_colors: list[Color] = [(0, 0, 0)] * self.n
        self.position = 0.0
        self.direction = 1
        self.hue_t = 0.0  # degrees the hue has rotated from eye_color

    def _current_color(self) -> Color:
        if self.hue_t == 0.0 and self.saturation == 1.0:
            return self.eye_color
        return colors.adjust_hsv(
            self.eye_color,
            hue_shift=self.hue_t / 360.0,
            saturation=self.saturation,
        )

    def tick(self, dt: float):
        self.trail.decay(dt)
        self.hue_t = wrap(self.hue_t + self.hue_cycle * dt, 360.0)
        color = self._current_color()

        # Paint every pixel the head sweeps over this frame, so fast eyes
        # don't leave gaps in the trail
        new_position = (
            self.position + self.direction * self._BASE_SPEED * self.speed * dt
        )
        lo = max(0, int(min(self.position, new_position)))
        hi = min(self.n - 1, int(max(self.position, new_position)))
        for i in range(lo, hi + 1):
            self.trail[i] = 1.0
            self.trail_colors[i] = color

        # Render: each pixel fades out in the color it was painted with
        for i, heat in enumerate(self.trail):
            self.pixels[i] = colors.scale(self.trail_colors[i], heat)

        # Move and bounce off the strip ends
        self.position = new_position
        if self.position >= self.n - 1:
            self.position = self.n - 1
            self.direction = -1
        elif self.position <= 0:
            self.position = 0
            self.direction = 1
