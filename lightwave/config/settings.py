"""
Configuration settings for LightWave-Server.

This module defines the configuration settings for the LightWave-Server application.
Settings can be configured via environment variables or with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

import board


class LogLevel(str, Enum):
    """Log level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LEDMode(str, Enum):
    """LED controller mode options."""
    REAL = "real"  # Control real LEDs
    MOCK = "mock"  # Use mock LED implementation


@dataclass
class ServerSettings:
    """Server configuration settings."""
    host: str = os.getenv("LIGHTWAVE_HOST", "0.0.0.0")
    port: int = int(os.getenv("LIGHTWAVE_PORT", "8080"))
    debug: bool = os.getenv("LIGHTWAVE_DEBUG", "false").lower() == "true"
    log_level: LogLevel = LogLevel(os.getenv("LIGHTWAVE_LOG_LEVEL", "INFO"))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv("LIGHTWAVE_CORS_ORIGINS", "*").split(","))


@dataclass
class LEDSettings:
    """LED controller configuration settings."""
    count: int = int(os.getenv("LIGHTWAVE_LED_COUNT", "300"))
    pin = getattr(board, os.getenv("LIGHTWAVE_LED_PIN", "D18"))
    mode: LEDMode = LEDMode(os.getenv("LIGHTWAVE_LED_MODE", "real").lower())
    brightness: float = float(os.getenv("LIGHTWAVE_LED_BRIGHTNESS", "0.5"))
    auto_write: bool = os.getenv("LIGHTWAVE_LED_AUTO_WRITE", "false").lower() == "true"
    
    # Default colors as RGB tuples
    default_color: Tuple[int, int, int] = (0, 0, 255)  # Default to blue


@dataclass
class EffectSettings:
    """Effect system configuration settings."""
    # Default frames per second for effects
    default_fps: float = float(os.getenv("LIGHTWAVE_EFFECT_DEFAULT_FPS", "30"))
    # Maximum allowed FPS
    max_fps: float = float(os.getenv("LIGHTWAVE_EFFECT_MAX_FPS", "60"))
    # Path to effects directory (for dynamic loading)
    effects_path: str = os.getenv("LIGHTWAVE_EFFECTS_PATH", "lightwave/effects")


@dataclass
class Settings:
    """Global application settings."""
    server: ServerSettings = field(default_factory=ServerSettings)
    led: LEDSettings = field(default_factory=LEDSettings)
    effect: EffectSettings = field(default_factory=EffectSettings)
    
    @property
    def is_mock_mode(self) -> bool:
        """Check if the LED controller is in mock mode."""
        return self.led.mode == LEDMode.MOCK
    
    @property
    def is_debug_mode(self) -> bool:
        """Check if the server is in debug mode."""
        return self.server.debug


# Create global settings instance
settings = Settings()