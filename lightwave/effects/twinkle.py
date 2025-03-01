"""
Twinkle effect for LightWave-Server.

This module provides a twinkling effect that simulates stars or sparkles.
"""

import math
import random
import time
from typing import Dict, List, Tuple, Set

from lightwave.effects.base import Effect, ParameterSpec, ParameterType
from lightwave.utils import get_logger, ColorValue, ColorType

logger = get_logger(__name__)


class TwinkleEffect(Effect):
    """
    Twinkle effect that simulates stars or sparkles.
    
    This effect creates a twinkling pattern where random LEDs light up
    and fade out, with customizable density, colors, and other parameters.
    """
    
    # Define parameters with metadata
    parameters = [
        ParameterSpec(
            name="density",
            type=ParameterType.FLOAT,
            description="Density of twinkles (0.0-1.0)",
            default=0.1,
            min_value=0.01,
            max_value=1.0,
        ),
        ParameterSpec(
            name="background_color",
            type=ParameterType.COLOR,
            description="Background color",
            default=(0, 0, 0),  # Black (off)
        ),
        ParameterSpec(
            name="twinkle_color",
            type=ParameterType.COLOR,
            description="Color of twinkles",
            default=(255, 255, 255),  # White
        ),
        ParameterSpec(
            name="duration",
            type=ParameterType.FLOAT,
            description="Duration of each twinkle in seconds",
            default=1.0,
            min_value=0.1,
            max_value=5.0,
        ),
        ParameterSpec(
            name="multicolor",
            type=ParameterType.BOOL,
            description="Use random colors for twinkles",
            default=False,
        ),
        ParameterSpec(
            name="max_active",
            type=ParameterType.FLOAT,
            description="Maximum percentage of LEDs that can be active at once",
            default=0.3,
            min_value=0.01,
            max_value=1.0,
        ),
    ]
    
    def __init__(self, controller, **kwargs):
        """Initialize the twinkle effect."""
        super().__init__(controller, **kwargs)
        
        # Initialize state
        self._twinkles = {}  # Map of pixel index to (start_time, duration, color)
        
        # Set initial FPS
        self.fps = 30
    
    def get_random_color(self) -> ColorValue:
        """
        Get a random bright color.
        
        Returns:
            A random color as an RGB tuple
        """
        # Generate a color where at least one channel is at full brightness
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        
        # Ensure at least one channel is bright
        max_val = max(r, g, b)
        if max_val < 180:  # Not bright enough
            scale = 255 / max_val if max_val > 0 else 1
            r = min(255, int(r * scale))
            g = min(255, int(g * scale))
            b = min(255, int(b * scale))
        
        return (r, g, b)
    
    def render_frame(self) -> None:
        """Render a single frame of the twinkle effect."""
        # Get parameters
        density = self.get_parameter("density")
        background_color = self.get_parameter("background_color")
        twinkle_color = self.get_parameter("twinkle_color")
        duration = self.get_parameter("duration")
        multicolor = self.get_parameter("multicolor")
        max_active = self.get_parameter("max_active")
        
        # Get the current time
        current_time = time.time()
        
        # Initialize all pixels to the background color
        for i in range(self.controller.count):
            if i not in self._twinkles:
                self.controller.set_pixel(i, background_color)
        
        # Remove expired twinkles
        expired = []
        for pixel, (start_time, pixel_duration, _) in self._twinkles.items():
            if current_time > start_time + pixel_duration:
                expired.append(pixel)
                self.controller.set_pixel(pixel, background_color)
        
        for pixel in expired:
            del self._twinkles[pixel]
        
        # Add new twinkles
        max_twinkles = int(self.controller.count * max_active)
        if (len(self._twinkles) < max_twinkles and
                random.random() < density / self.fps):
            
            # Find an available pixel
            available_pixels = [i for i in range(self.controller.count)
                                if i not in self._twinkles]
            
            if available_pixels:
                # Pick a random pixel
                pixel = random.choice(available_pixels)
                
                # Pick a color
                if multicolor:
                    color = self.get_random_color()
                else:
                    color = twinkle_color
                
                # Add the twinkle with a random duration
                pixel_duration = duration * (0.5 + random.random())
                self._twinkles[pixel] = (current_time, pixel_duration, color)
        
        # Update active twinkles
        for pixel, (start_time, pixel_duration, color) in self._twinkles.items():
            # Calculate the progress of the twinkle
            progress = (current_time - start_time) / pixel_duration
            
            # Use sine wave for smooth fade in and out
            brightness = math.sin(progress * math.pi)
            
            # Calculate the color
            r = int(background_color[0] + (color[0] - background_color[0]) * brightness)
            g = int(background_color[1] + (color[1] - background_color[1]) * brightness)
            b = int(background_color[2] + (color[2] - background_color[2]) * brightness)
            
            # Set the pixel color
            self.controller.set_pixel(pixel, (r, g, b))
        
        # Update the display
        self.controller.show()