"""
Color utilities for LightWave-Server.

This module provides utilities for working with colors, including 
conversion between different color formats and validation.
"""

import re
from enum import Enum
from typing import Dict, Tuple, Union, Literal, Any, overload, TypeVar, cast

# Type definitions for color values
ColorValue = Tuple[int, int, int]  # RGB values as a tuple
ColorType = Union[ColorValue, str]  # Either RGB tuple or hex string


def hex_to_rgb(hex_color: str) -> ColorValue:
    """
    Convert a hex color string to an RGB tuple.
    
    Args:
        hex_color: A hex color string (e.g., '#ff0000' or 'ff0000')
        
    Returns:
        An RGB tuple with values from 0-255
        
    Raises:
        ValueError: If the hex string is invalid
    """
    # Remove the '#' if present
    hex_color = hex_color.lstrip('#')
    
    # Validate hex format
    if not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
        raise ValueError(f"Invalid hex color format: {hex_color}")
    
    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    return (r, g, b)


def rgb_to_hex(rgb: ColorValue) -> str:
    """
    Convert an RGB tuple to a hex color string.
    
    Args:
        rgb: An RGB tuple with values from 0-255
        
    Returns:
        A hex color string (e.g., '#ff0000')
        
    Raises:
        ValueError: If any RGB value is outside the valid range
    """
    r, g, b = rgb
    
    # Validate RGB values
    if not all(0 <= c <= 255 for c in rgb):
        raise ValueError(f"Invalid RGB values: {rgb}")
    
    return f"#{r:02x}{g:02x}{b:02x}"


def normalize_color(color: ColorType) -> ColorValue:
    """
    Normalize a color value to an RGB tuple.
    
    Args:
        color: Either an RGB tuple or a hex color string
        
    Returns:
        An RGB tuple with values from 0-255
        
    Raises:
        ValueError: If the color format is invalid
    """
    if isinstance(color, tuple) and len(color) == 3:
        if not all(isinstance(c, int) and 0 <= c <= 255 for c in color):
            raise ValueError(f"Invalid RGB values: {color}")
        return color
    elif isinstance(color, str):
        return hex_to_rgb(color)
    else:
        raise ValueError(f"Invalid color format: {color}")


# Common color constants
class Color:
    """Common color constants."""
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    PURPLE = (128, 0, 128)
    ORANGE = (255, 165, 0)
    PINK = (255, 192, 203)