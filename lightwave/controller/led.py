"""
LED controller classes for LightWave-Server.

This module provides classes for controlling LED strips, including
a base controller interface and concrete implementations for real
and mock LED hardware.
"""

import abc
import time
from typing import List, Optional, Protocol, Tuple, Union

import neopixel

from lightwave.config import settings
from lightwave.utils import get_logger, normalize_color, ColorType, ColorValue

logger = get_logger(__name__)


class LEDController(abc.ABC):
    """
    Abstract base class for LED controllers.
    
    This class defines the interface that all LED controllers must implement.
    """
    
    @property
    @abc.abstractmethod
    def count(self) -> int:
        """Get the number of LEDs in the strip."""
        pass
    
    @property
    @abc.abstractmethod
    def brightness(self) -> float:
        """Get the current brightness level."""
        pass
    
    @brightness.setter
    @abc.abstractmethod
    def brightness(self, value: float) -> None:
        """Set the brightness level."""
        pass
    
    @abc.abstractmethod
    def set_pixel(self, index: int, color: ColorType) -> None:
        """
        Set the color of a specific pixel.
        
        Args:
            index: The index of the pixel to set
            color: The color to set the pixel to
        """
        pass
    
    @abc.abstractmethod
    def set_all(self, color: ColorType) -> None:
        """
        Set all pixels to the same color.
        
        Args:
            color: The color to set all pixels to
        """
        pass
    
    @abc.abstractmethod
    def clear(self) -> None:
        """Turn off all pixels."""
        pass
    
    @abc.abstractmethod
    def show(self) -> None:
        """Update the LED strip with the current pixel values."""
        pass
    
    @abc.abstractmethod
    def get_pixel(self, index: int) -> ColorValue:
        """
        Get the color of a specific pixel.
        
        Args:
            index: The index of the pixel to get
            
        Returns:
            The color of the pixel as an RGB tuple
        """
        pass
    
    @abc.abstractmethod
    def get_all(self) -> List[ColorValue]:
        """
        Get the colors of all pixels.
        
        Returns:
            A list of RGB tuples representing the colors of all pixels
        """
        pass


class RealLEDController(LEDController):
    """
    LED controller for controlling real NeoPixel LEDs.
    
    This class provides a concrete implementation of the LEDController interface
    for controlling real NeoPixel LED hardware.
    """
    
    def __init__(
        self,
        pin=settings.led.pin,
        count: int = settings.led.count,
        auto_write: bool = settings.led.auto_write,
        brightness: float = settings.led.brightness
    ):
        """
        Initialize the LED controller.
        
        Args:
            pin: The GPIO pin connected to the LED strip
            count: The number of LEDs in the strip
            auto_write: Whether to automatically update the LEDs after each change
            brightness: The initial brightness level (0.0-1.0)
        """
        logger.info(f"Initializing NeoPixel LED controller with {count} LEDs on pin {pin}")
        
        # Validate parameters
        if count <= 0:
            raise ValueError(f"LED count must be positive, got {count}")
        
        if not 0.0 <= brightness <= 1.0:
            raise ValueError(f"Brightness must be between 0.0 and 1.0, got {brightness}")
        
        # Store parameters
        self._count = count
        self._auto_write = auto_write
        
        # Initialize NeoPixel object
        try:
            self._pixels = neopixel.NeoPixel(
                pin,
                count,
                auto_write=auto_write,
                pixel_order=neopixel.GRB
            )
            self._pixels.brightness = brightness
        except Exception as e:
            logger.error(f"Failed to initialize NeoPixel: {e}")
            raise
        
        logger.debug("NeoPixel LED controller initialized successfully")
    
    @property
    def count(self) -> int:
        """Get the number of LEDs in the strip."""
        return self._count
    
    @property
    def brightness(self) -> float:
        """Get the current brightness level."""
        return self._pixels.brightness
    
    @brightness.setter
    def brightness(self, value: float) -> None:
        """
        Set the brightness level.
        
        Args:
            value: The brightness level (0.0-1.0)
        """
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Brightness must be between 0.0 and 1.0, got {value}")
        
        logger.debug(f"Setting brightness to {value}")
        self._pixels.brightness = value
        
        if not self._auto_write:
            self.show()
    
    def set_pixel(self, index: int, color: ColorType) -> None:
        """
        Set the color of a specific pixel.
        
        Args:
            index: The index of the pixel to set
            color: The color to set the pixel to
        """
        if not 0 <= index < self._count:
            raise IndexError(f"Pixel index out of range: {index}")
        
        rgb = normalize_color(color)
        logger.debug(f"Setting pixel {index} to {rgb}")
        
        try:
            self._pixels[index] = rgb
            
            if not self._auto_write:
                self.show()
        except Exception as e:
            logger.error(f"Failed to set pixel {index} to {rgb}: {e}")
            raise
    
    def set_all(self, color: ColorType) -> None:
        """
        Set all pixels to the same color.
        
        Args:
            color: The color to set all pixels to
        """
        rgb = normalize_color(color)
        logger.debug(f"Setting all pixels to {rgb}")
        
        try:
            self._pixels.fill(rgb)
            
            if not self._auto_write:
                self.show()
        except Exception as e:
            logger.error(f"Failed to set all pixels to {rgb}: {e}")
            raise
    
    def clear(self) -> None:
        """Turn off all pixels."""
        logger.debug("Clearing all pixels")
        self.set_all((0, 0, 0))
    
    def show(self) -> None:
        """Update the LED strip with the current pixel values."""
        logger.debug("Updating LED strip")
        try:
            self._pixels.show()
        except Exception as e:
            logger.error(f"Failed to update LED strip: {e}")
            raise
    
    def get_pixel(self, index: int) -> ColorValue:
        """
        Get the color of a specific pixel.
        
        Args:
            index: The index of the pixel to get
            
        Returns:
            The color of the pixel as an RGB tuple
        """
        if not 0 <= index < self._count:
            raise IndexError(f"Pixel index out of range: {index}")
        
        return tuple(self._pixels[index])
    
    def get_all(self) -> List[ColorValue]:
        """
        Get the colors of all pixels.
        
        Returns:
            A list of RGB tuples representing the colors of all pixels
        """
        return [tuple(self._pixels[i]) for i in range(self._count)]


class MockLEDController(LEDController):
    """
    Mock LED controller for testing without hardware.
    
    This class provides a concrete implementation of the LEDController interface
    that simulates an LED strip without requiring actual hardware.
    """
    
    def __init__(
        self,
        count: int = settings.led.count,
        auto_write: bool = settings.led.auto_write,
        brightness: float = settings.led.brightness
    ):
        """
        Initialize the mock LED controller.
        
        Args:
            count: The number of virtual LEDs to simulate
            auto_write: Whether to automatically update the LEDs after each change
            brightness: The initial brightness level (0.0-1.0)
        """
        logger.info(f"Initializing mock LED controller with {count} LEDs")
        
        # Validate parameters
        if count <= 0:
            raise ValueError(f"LED count must be positive, got {count}")
        
        if not 0.0 <= brightness <= 1.0:
            raise ValueError(f"Brightness must be between 0.0 and 1.0, got {brightness}")
        
        # Store parameters
        self._count = count
        self._auto_write = auto_write
        self._brightness = brightness
        
        # Initialize pixel array
        self._pixels = [(0, 0, 0) for _ in range(count)]
        
        logger.debug("Mock LED controller initialized successfully")
    
    @property
    def count(self) -> int:
        """Get the number of LEDs in the strip."""
        return self._count
    
    @property
    def brightness(self) -> float:
        """Get the current brightness level."""
        return self._brightness
    
    @brightness.setter
    def brightness(self, value: float) -> None:
        """
        Set the brightness level.
        
        Args:
            value: The brightness level (0.0-1.0)
        """
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Brightness must be between 0.0 and 1.0, got {value}")
        
        logger.debug(f"Setting brightness to {value}")
        self._brightness = value
        
        if not self._auto_write:
            self.show()
    
    def set_pixel(self, index: int, color: ColorType) -> None:
        """
        Set the color of a specific pixel.
        
        Args:
            index: The index of the pixel to set
            color: The color to set the pixel to
        """
        if not 0 <= index < self._count:
            raise IndexError(f"Pixel index out of range: {index}")
        
        rgb = normalize_color(color)
        logger.debug(f"Setting pixel {index} to {rgb}")
        
        self._pixels[index] = rgb
        
        if not self._auto_write:
            self.show()
    
    def set_all(self, color: ColorType) -> None:
        """
        Set all pixels to the same color.
        
        Args:
            color: The color to set all pixels to
        """
        rgb = normalize_color(color)
        logger.debug(f"Setting all pixels to {rgb}")
        
        self._pixels = [rgb for _ in range(self._count)]
        
        if not self._auto_write:
            self.show()
    
    def clear(self) -> None:
        """Turn off all pixels."""
        logger.debug("Clearing all pixels")
        self.set_all((0, 0, 0))
    
    def show(self) -> None:
        """Update the LED strip with the current pixel values."""
        logger.debug("Updating mock LED strip")
        logger.debug(f"Current state: {self._pixels[:5]}{'...' if self._count > 5 else ''}")
    
    def get_pixel(self, index: int) -> ColorValue:
        """
        Get the color of a specific pixel.
        
        Args:
            index: The index of the pixel to get
            
        Returns:
            The color of the pixel as an RGB tuple
        """
        if not 0 <= index < self._count:
            raise IndexError(f"Pixel index out of range: {index}")
        
        return self._pixels[index]
    
    def get_all(self) -> List[ColorValue]:
        """
        Get the colors of all pixels.
        
        Returns:
            A list of RGB tuples representing the colors of all pixels
        """
        return self._pixels