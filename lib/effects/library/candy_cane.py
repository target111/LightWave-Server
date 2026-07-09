from lib.effects.anim import wrap
from lib.effects.base import Color, EffectBase, option


class CandyCane(EffectBase):
    """
    Rotating Red and White stripes resembling a candy cane.
    """

    speed: float = option(
        1.0, "Speed multiplier (1.0 = 20 pixels/second)", min=0.0
    )
    stripe_width: int = option(5, "Width of each stripe in pixels", min=1)
    color1: Color = option((255, 0, 0), "First stripe color")
    color2: Color = option((255, 255, 255), "Second stripe color")
    direction: str = option(
        "forward", "Rotation direction", choices=["forward", "reverse"]
    )

    _BASE_SPEED = 20.0  # pixels/second at speed=1.0

    def setup(self):
        self.offset = 0.0

    def tick(self, dt: float):
        current_offset = int(self.offset)

        for i in range(self.n):
            if ((i + current_offset) // self.stripe_width) % 2 == 0:
                self.pixels[i] = self.color1
            else:
                self.pixels[i] = self.color2

        step = self._BASE_SPEED * self.speed * dt
        if self.direction == "reverse":
            step = -step
        self.offset = wrap(self.offset + step, self.stripe_width * 2)
