import random

from lib.effects.library.starry_night import StarryNight


class StarryNightColor(StarryNight):
    """
    Randomly fades multi-colored stars in and out smoothly.
    """

    CONFIG_SCHEMA = [
        {
            "name": "density",
            "type": "float",
            "default": 1.0,
            "description": "Star density multiplier (1.0 = normal)",
        },
        {
            "name": "fade_time",
            "type": "float",
            "default": 1.4,
            "description": "Seconds for a star to fade in (and out again)",
        },
    ]

    PALETTE: list[tuple[int, int, int]] = [
        (255, 255, 255),
        (200, 200, 255),
        (255, 240, 150),
        (255, 200, 100),
        (150, 150, 255),
        (255, 180, 220),
    ]

    def _pick_color(self) -> tuple[int, int, int]:
        return random.choice(self.PALETTE)
