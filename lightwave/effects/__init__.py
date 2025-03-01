"""
Effects module for LightWave-Server.

This module provides base classes and implementations for LED effects.
"""

from .base import Effect, ParameterType, ParameterSpec
from .registry import EffectRegistry
from .rainbow import RainbowEffect
from .pulse import PulseEffect
from .twinkle import TwinkleEffect

__all__ = [
    "Effect",
    "ParameterType",
    "ParameterSpec",
    "EffectRegistry",
    "RainbowEffect",
    "PulseEffect",
    "TwinkleEffect"
]