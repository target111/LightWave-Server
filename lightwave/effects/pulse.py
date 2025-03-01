"""
Pulse effect for LightWave-Server.

This module provides a pulsing effect that fades LEDs between colors.
"""

import math
import time
from typing import List, Tuple

from lightwave.effects.base import Effect, ParameterSpec, ParameterType
from lightwave.utils import get_logger, ColorValue, ColorType, normalize_color

logger = get_logger(__name__)


class PulseEffect(Effect):
    """
    Pulse effect that fades LEDs between colors.
    
    This effect creates a pulsing pattern that fades between colors,
    with customizable speed, colors, and other parameters.
    """
    
    # Define parameters with metadata
    parameters = [
        ParameterSpec(
            name="speed",
            type=ParameterType.FLOAT,
            description="Speed of the pulse (cycles per second)",
            default=1.0,
            min_value=0.1,
            max_value=10.0,
        ),
        ParameterSpec(
            name="primary_color",
            type=ParameterType.COLOR,
            description="Primary color to pulse to",
            default=(255, 0, 0),  # Red
        ),
        ParameterSpec(
            name="secondary_color",
            type=ParameterType.COLOR,
            description="Secondary color to pulse from",
            default=(0, 0, 0),  # Black (off)
        ),
        ParameterSpec(
            name="wave",
            type=ParameterType.ENUM,
            description="Waveform of the pulse",
            default="sine",
            options=["sine", "triangle", "square", "sawtooth"],
        ),
        ParameterSpec(
            name="min_brightness",
            type=ParameterType.FLOAT,
            description="Minimum brightness during pulse",
            default=0.0,
            min_value=0.0,
            max_value=1.0,
        ),
        ParameterSpec(
            name="max_brightness",
            type=ParameterType.FLOAT,
            description="Maximum brightness during pulse",
            default=1.0,
            min_value=0.0,
            max_value=1.0,
        ),
    ]
    
    def __init__(self, controller, **kwargs):
        """Initialize the pulse effect."""
        super().__init__(controller, **kwargs)
        
        # Initialize state
        self._phase = 0.0
        
        # Set initial FPS
        self.fps = 30
    
    def get_wave_value(self, phase: float, wave_type: str) -> float:
        """
        Get a value from a waveform at a specific phase.
        
        Args:
            phase: Phase of the wave (0.0-1.0)
            wave_type: Type of waveform (sine, triangle, square, sawtooth)
            
        Returns:
            A value between 0.0 and 1.0
        """
        if wave_type == "sine":
            return (math.sin(phase * 2 * math.pi - math.pi / 2) + 1) / 2
        elif wave_type == "triangle":
            return 1.0 - 2.0 * abs(phase - 0.5) if phase <= 1.0 else 0.0
        elif wave_type == "square":
            return 1.0 if phase < 0.5 else 0.0
        elif wave_type == "sawtooth":
            return phase
        else:
            # Default to sine if unknown
            return (math.sin(phase * 2 * math.pi - math.pi / 2) + 1) / 2
    
    def interpolate_color(self, color1: ColorValue, color2: ColorValue, ratio: float) -> ColorValue:
        """
        Interpolate between two colors.
        
        Args:
            color1: First color
            color2: Second color
            ratio: Ratio between the colors (0.0 = color1, 1.0 = color2)
            
        Returns:
            Interpolated color
        """
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        
        return (r, g, b)
    
    def render_frame(self) -> None:
        """Render a single frame of the pulse effect."""
        # Get parameters
        speed = self.get_parameter("speed")
        primary_color = self.get_parameter("primary_color")
        secondary_color = self.get_parameter("secondary_color")
        wave_type = self.get_parameter("wave")
        min_brightness = self.get_parameter("min_brightness")
        max_brightness = self.get_parameter("max_brightness")
        
        # Update phase based on speed
        self._phase += speed / self.fps
        self._phase %= 1.0  # Keep it in the range 0-1
        
        # Calculate the wave value
        wave_value = self.get_wave_value(self._phase, wave_type)
        
        # Scale the wave value to the brightness range
        brightness = min_brightness + wave_value * (max_brightness - min_brightness)
        
        # Interpolate between colors
        color = self.interpolate_color(secondary_color, primary_color, wave_value)
        
        # Set all pixels to the same color
        self.controller.set_all(color)
        
        # Set the brightness
        self.controller.brightness = brightness
        
        # Update the display
        self.controller.show()