"""
Rainbow effect for LightWave-Server.

This module provides a rainbow effect that cycles colors across the LED strip.
"""

import math
import time
from typing import Tuple

from lightwave.effects.base import Effect, ParameterSpec, ParameterType
from lightwave.utils import get_logger, ColorValue

logger = get_logger(__name__)


class RainbowEffect(Effect):
    """
    Rainbow effect that cycles colors across the LED strip.
    
    This effect creates a rainbow pattern that cycles across all LEDs,
    with customizable speed, saturation, and other parameters.
    """
    
    # Define parameters with metadata
    parameters = [
        ParameterSpec(
            name="speed",
            type=ParameterType.FLOAT,
            description="Speed of the rainbow cycle (cycles per second)",
            default=0.5,
            min_value=0.01,
            max_value=5.0,
        ),
        ParameterSpec(
            name="saturation",
            type=ParameterType.FLOAT,
            description="Color saturation (0.0-1.0)",
            default=1.0,
            min_value=0.0,
            max_value=1.0,
        ),
        ParameterSpec(
            name="brightness",
            type=ParameterType.FLOAT,
            description="Maximum brightness override (0.0-1.0)",
            default=1.0,
            min_value=0.0,
            max_value=1.0,
        ),
        ParameterSpec(
            name="width",
            type=ParameterType.FLOAT,
            description="Width of the rainbow pattern relative to strip length",
            default=1.0,
            min_value=0.1,
            max_value=5.0,
        ),
        ParameterSpec(
            name="reverse",
            type=ParameterType.BOOL,
            description="Reverse the direction of the rainbow",
            default=False,
        ),
    ]
    
    def __init__(self, controller, **kwargs):
        """Initialize the rainbow effect."""
        super().__init__(controller, **kwargs)
        
        # Initialize state
        self._offset = 0.0
        
        # Set initial FPS
        self.fps = 30
    
    def wheel(self, pos: float) -> ColorValue:
        """
        Get a color from the color wheel.
        
        Args:
            pos: Position on the color wheel (0-255)
            
        Returns:
            The color at the specified position as an RGB tuple
        """
        pos = int(pos) % 256
        
        saturation = self.get_parameter("saturation")
        
        if pos < 85:
            r = int(pos * 3 * saturation)
            g = int((255 - pos * 3) * saturation)
            b = 0
        elif pos < 170:
            pos -= 85
            r = int((255 - pos * 3) * saturation)
            g = 0
            b = int(pos * 3 * saturation)
        else:
            pos -= 170
            r = 0
            g = int(pos * 3 * saturation)
            b = int((255 - pos * 3) * saturation)
        
        return (r, g, b)
    
    def render_frame(self) -> None:
        """Render a single frame of the rainbow effect."""
        # Get parameters
        speed = self.get_parameter("speed")
        width = self.get_parameter("width")
        brightness_override = self.get_parameter("brightness")
        reverse = self.get_parameter("reverse")
        
        # Update the offset based on the speed
        self._offset += speed / self.fps
        self._offset %= 256.0  # Keep it in the range 0-255
        
        # Calculate scaling factors
        count = self.controller.count
        scale = 256.0 / count * width
        
        # Render the frame
        for i in range(count):
            # Calculate the position on the color wheel
            if reverse:
                pos = (255 - int((i * scale + self._offset) % 256))
            else:
                pos = int((i * scale + self._offset) % 256)
            
            # Get the color from the wheel
            color = self.wheel(pos)
            
            # Set the pixel color
            self.controller.set_pixel(i, color)
        
        # Update the display
        self.controller.brightness = brightness_override
        self.controller.show()