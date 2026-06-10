import random

from lib.effects.starry_night import StarryNight


class StarryNightColor(StarryNight):
    """
    Randomly fades multi-colored stars in and out smoothly.
    """

    CONFIG_SCHEMA = [
        {
            "name": "density",
            "type": "float",
            "default": 0.02,
            "description": "Density of stars (probability per frame)",
        },
        {
            "name": "speed",
            "type": "int",
            # Original fade was 10/frame at 20 FPS; ~3/frame at 60 FPS.
            "default": 3,
            "description": "Fade speed (brightness change per frame)",
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
