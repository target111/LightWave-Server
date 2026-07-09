"""Starter effect — copy this file, rename it (drop the leading `_`),
and it is registered automatically. Files starting with `_` are ignored.

Preview it without hardware:

    uv run python -m lib.effects.preview Comet speed=2 color=0,200,255
"""

from lib.effects import colors
from lib.effects.anim import FadeBuffer
from lib.effects.base import Color, EffectBase, option


class Comet(EffectBase):
    """
    A comet that sweeps across the strip, leaving a fading tail.
    """

    # This docstring is the effect description shown by the API.

    # Options: one line each. The type comes from the annotation
    # (int, float, bool, Color, or str); values arriving over the API are
    # coerced, checked against min/max (or choices), and set as instance
    # attributes. A str option must list its `choices` and renders as a
    # dropdown.
    #
    # Conventions: times in seconds, sizes in pixels, rates per second,
    # probabilities 0.0-1.0. Unitless knobs are multipliers where 1.0 is
    # the designed look — keep the tuned base value in a named constant.
    speed: float = option(
        1.0, "Speed multiplier (1.0 = 30 pixels/second)", min=0.0
    )
    color: Color = option((0, 200, 255), "Comet color")
    tail_fade: float = option(
        1.0, "Seconds for the tail to fade out", min=0.0
    )
    direction: str = option(
        "forward", "Sweep direction", choices=["forward", "reverse"]
    )

    _BASE_SPEED = 30.0  # pixels/second at speed=1.0

    def setup(self):
        # Runs once, after options are resolved. `self.n` is the number
        # of pixels. No __init__ needed.
        self.position = 0.0
        self.tail = FadeBuffer(self.n, self.tail_fade)

    def tick(self, dt: float):
        # Runs ~TARGET_FPS times per second; dt is the elapsed time in
        # seconds since the last frame. Scale all movement by dt so the
        # animation is frame-rate independent.
        #
        # Draw by writing (r, g, b) tuples into self.pixels — the loop
        # pushes the buffer to the LEDs after every tick. The buffer
        # persists between frames; self.clear() / self.fill(color) reset
        # it. See lib.effects.colors and lib.effects.anim for helpers.
        step = self._BASE_SPEED * self.speed * dt
        if self.direction == "reverse":
            step = -step
        self.position = (self.position + step) % self.n  # wrap either way

        self.tail.decay(dt)
        self.tail[int(self.position)] = 1.0

        for i, heat in enumerate(self.tail):
            self.pixels[i] = colors.scale(self.color, heat)

    def teardown(self):
        # Optional: release sockets/files when the effect stops.
        pass
