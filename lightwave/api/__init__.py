"""
API module for LightWave-Server.

This module provides a FastAPI-based HTTP API for controlling the LED strip.
"""

from .server import create_app, LightWaveAPI

__all__ = ["create_app", "LightWaveAPI"]