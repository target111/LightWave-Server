import os
from dataclasses import dataclass, field
from typing import Literal

from lib.drivers.base import LEDDriver


@dataclass(frozen=True)
class Settings:
    # default_factory so the env is read when Settings() is created,
    # not once at import time
    led_count: int = field(
        default_factory=lambda: int(os.getenv("LED_COUNT", "300"))
    )
    led_pin: str = field(default_factory=lambda: os.getenv("LED_PIN", "D18"))
    backend: Literal["neopixel", "mock"] = field(
        default_factory=lambda: os.getenv("LED_BACKEND", "neopixel")  # type: ignore[assignment,return-value]
    )
    broadcast_fps: int = field(
        default_factory=lambda: int(os.getenv("BROADCAST_FPS", "30"))
    )


def build_driver(settings: Settings) -> LEDDriver:
    """Backend factory. `neopixel` imports are deferred so non-Pi dev works."""
    if settings.backend == "mock":
        from lib.drivers.mock_driver import MockDriver

        return MockDriver(settings.led_count)

    from lib.drivers.neopixel_driver import NeoPixelDriver

    return NeoPixelDriver(settings.led_pin, settings.led_count)
