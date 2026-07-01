import random

from lib.effects.base import Color, EffectBase, option


class SnowSparkle(EffectBase):
    """
    Background with random white sparkles popping in and out.
    """

    bg_color: Color = option((64, 160, 43), "Background color")
    sparkle_color: Color = option((255, 255, 255), "Sparkle color")
    duration: float = option(
        0.05, "Duration of a sparkle in seconds", min=0.0
    )
    interval: float = option(
        0.05, "Base interval between sparkles in seconds", min=0.0
    )

    def setup(self):
        self.sparkle_on = False
        self.timer = 0.0
        self.next_event_time = 0.0
        self.active_pixel = 0

    def tick(self, dt: float):
        self.timer += dt

        if self.timer >= self.next_event_time:
            self.timer = 0.0
            if self.sparkle_on:
                self.sparkle_on = False
                self.next_event_time = random.uniform(0.02, self.interval * 2)
            else:
                self.sparkle_on = True
                self.active_pixel = random.randint(0, self.n - 1)
                self.next_event_time = self.duration

        self.fill(self.bg_color)
        if self.sparkle_on:
            self.pixels[self.active_pixel] = self.sparkle_color
