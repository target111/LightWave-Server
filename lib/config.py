from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from lib.drivers.base import LEDDriver


class Settings(BaseSettings):
    """Read from the environment at construction time; invalid values
    (unknown backend, non-numeric counts) fail fast with a clear error."""

    model_config = SettingsConfigDict(frozen=True)

    led_count: int = 300
    led_pin: str = "D18"
    backend: Literal["neopixel", "mock"] = Field(
        "neopixel", validation_alias="LED_BACKEND"
    )
    broadcast_fps: int = 30
    presets_file: Path = Path("presets.json")


def build_driver(settings: Settings) -> LEDDriver:
    """Backend factory. `neopixel` imports are deferred so non-Pi dev works."""
    if settings.backend == "mock":
        from lib.drivers.mock_driver import MockDriver

        return MockDriver(settings.led_count)

    from lib.drivers.neopixel_driver import NeoPixelDriver

    return NeoPixelDriver(settings.led_pin, settings.led_count)
