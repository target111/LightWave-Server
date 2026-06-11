import random

from lib.effects.base import EffectBase


class MatrixRain(EffectBase):
    """
    Green 'code' drops that are guaranteed to reach the bottom of the strip.
    """

    CONFIG_SCHEMA = [
        {
            "name": "spawn_rate",
            "type": "float",
            "default": 2.5,
            "description": "New drops per second",
        },
        {
            "name": "trail_length",
            "type": "int",
            "default": 20,
            "description": "Length of the drop trail",
        },
        {
            "name": "head_color",
            "type": "color",
            "default": (180, 255, 180),
            "description": "Color of the drop head",
        },
        {
            "name": "tail_color",
            "type": "color",
            "default": (0, 255, 0),
            "description": "Color of the drop trail",
        },
    ]

    spawn_rate: float
    trail_length: int
    head_color: tuple[int, int, int]
    tail_color: tuple[int, int, int]

    _MIN_SPEED = 10.0  # drop fall speed range in pixels/second
    _MAX_SPEED = 40.0

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.drops = []

    def tick(self, dt: float):
        # Spawn
        if random.random() < self.spawn_rate * dt:
            speed = random.uniform(self._MIN_SPEED, self._MAX_SPEED)
            self.drops.append([0.0, speed])

        pixel_buffer = {}
        active_drops = []

        for drop in self.drops:
            pos, speed = drop
            pos += speed * dt

            head_pixel = int(pos)

            if head_pixel - self.trail_length < self.led.count:
                active_drops.append([pos, speed])

                for i in range(self.trail_length):
                    pixel_index = head_pixel - i
                    if 0 <= pixel_index < self.led.count:
                        intensity = 1.0 - (i / self.trail_length)
                        current_val = pixel_buffer.get(pixel_index, 0.0)
                        pixel_buffer[pixel_index] = max(current_val, intensity)

        self.drops = active_drops

        for i in range(self.led.count):
            if i in pixel_buffer:
                intensity = pixel_buffer[i]
                color = self.head_color if intensity > 0.9 else self.tail_color
                r = int(color[0] * intensity)
                g = int(color[1] * intensity)
                b = int(color[2] * intensity)
                self.led.set_pixel(i, (r, g, b))
            else:
                self.led.set_pixel(i, (0, 0, 0))
