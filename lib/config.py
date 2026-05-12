import os
from dataclasses import dataclass
from typing import Literal

from lib.drivers.base import LEDDriver


@dataclass(frozen=True)
class Settings:
    led_count: int = int(os.getenv("LED_COUNT", "300"))
    led_pin: str = os.getenv("LED_PIN", "D18")
    backend: Literal["neopixel", "mock"] = os.getenv("LED_BACKEND", "neopixel")  # type: ignore[assignment]


def build_driver(settings: Settings) -> LEDDriver:
    """Backend factory. `neopixel` imports are deferred so non-Pi dev works."""
    if settings.backend == "mock":
        from lib.drivers.mock_driver import MockDriver

        return MockDriver(settings.led_count)

    from lib.drivers.neopixel_driver import NeoPixelDriver

    return NeoPixelDriver(settings.led_pin, settings.led_count)
