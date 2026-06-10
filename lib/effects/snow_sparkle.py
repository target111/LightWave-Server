import random

from lib.effects.base import EffectBase


class SnowSparkle(EffectBase):
    """
    Background with random white sparkles popping in and out.
    """

    CONFIG_SCHEMA = [
        {
            "name": "bg_color",
            "type": "color",
            "default": (64, 160, 43),
            "description": "Background color",
        },
        {
            "name": "sparkle_color",
            "type": "color",
            "default": (255, 255, 255),
            "description": "Sparkle color",
        },
        {
            "name": "duration",
            "type": "float",
            "default": 0.05,
            "description": "Duration of a sparkle in seconds",
        },
        {
            "name": "interval",
            "type": "float",
            "default": 0.05,
            "description": "Base interval between sparkles in seconds",
        },
    ]

    bg_color: tuple[int, int, int]
    sparkle_color: tuple[int, int, int]
    duration: float
    interval: float

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.state = 0  # 0 = Wait for sparkle, 1 = Sparkle active
        self.timer = 0.0
        self.next_event_time = 0.0
        self.active_pixel = -1

        self.led.set_color(self.bg_color)

    def tick(self, dt: float):
        self.timer += dt

        if self.state == 0:  # Waiting to sparkle
            if self.timer >= self.next_event_time:
                # Trigger sparkle
                self.active_pixel = random.randint(0, self.led.count - 1)
                self.led.set_pixel(self.active_pixel, self.sparkle_color)

                self.state = 1
                self.timer = 0.0
                self.next_event_time = self.duration

        elif self.state == 1:  # Sparkle is on
            if self.timer >= self.next_event_time:
                # Turn off sparkle
                if self.active_pixel != -1:
                    self.led.set_pixel(self.active_pixel, self.bg_color)

                self.state = 0
                self.timer = 0.0
                self.next_event_time = random.uniform(0.02, self.interval * 2)
