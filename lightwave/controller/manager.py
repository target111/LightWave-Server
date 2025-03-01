"""
LED manager module for LightWave-Server.

This module provides a higher-level manager for controlling LED strips
and managing effects.
"""

import time
from typing import Dict, List, Optional, Type, Union, Any

from lightwave.config import settings
from lightwave.utils import get_logger, ColorType
from lightwave.controller.led import LEDController, RealLEDController, MockLEDController

logger = get_logger(__name__)


class LEDManager:
    """
    High-level manager for controlling LED strips and managing effects.
    
    This class provides a higher-level interface for controlling LED strips
    and managing effects, with support for both real and mock hardware.
    """
    
    def __init__(self):
        """Initialize the LED manager."""
        logger.info("Initializing LED manager")
        
        # Choose controller implementation based on settings
        if settings.is_mock_mode:
            logger.info("Using mock LED controller")
            self._controller = MockLEDController(
                count=settings.led.count,
                auto_write=settings.led.auto_write,
                brightness=settings.led.brightness
            )
        else:
            logger.info("Using real LED controller")
            self._controller = RealLEDController(
                pin=settings.led.pin,
                count=settings.led.count,
                auto_write=settings.led.auto_write,
                brightness=settings.led.brightness
            )
        
        # Initialize state
        self._current_effect = None
        self._effect_parameters = {}
        
        # Turn off all LEDs on startup
        self.clear()
        
        logger.debug("LED manager initialized successfully")
    
    @property
    def controller(self) -> LEDController:
        """Get the LED controller."""
        return self._controller
    
    @property
    def current_effect(self):
        """Get the currently running effect."""
        return self._current_effect
    
    def set_brightness(self, brightness: float) -> None:
        """
        Set the brightness level of the LED strip.
        
        Args:
            brightness: The brightness level (0.0-1.0)
        """
        logger.info(f"Setting brightness to {brightness}")
        self._controller.brightness = brightness
    
    def set_color(self, color: ColorType) -> None:
        """
        Set all LEDs to the same color.
        
        Args:
            color: The color to set all LEDs to
        """
        logger.info(f"Setting all LEDs to color {color}")
        
        # Stop any running effect
        self.stop_effect()
        
        # Set color
        self._controller.set_all(color)
    
    def clear(self) -> None:
        """Turn off all LEDs."""
        logger.info("Turning off all LEDs")
        
        # Stop any running effect
        self.stop_effect()
        
        # Clear LEDs
        self._controller.clear()
    
    def start_effect(self, effect_class: Type, parameters: Dict[str, Any] = None) -> Any:
        """
        Start an effect on the LED strip.
        
        Args:
            effect_class: The effect class to instantiate
            parameters: Optional parameters to pass to the effect
            
        Returns:
            The instantiated effect
        """
        # Stop any running effect
        self.stop_effect()
        
        # Get parameters or use empty dict if None
        parameters = parameters or {}
        
        # Create and start the effect
        logger.info(f"Starting effect {effect_class.__name__} with parameters {parameters}")
        
        try:
            effect = effect_class(self._controller, **parameters)
            effect.start()
            
            # Store the effect and parameters
            self._current_effect = effect
            self._effect_parameters = parameters
            
            return effect
        except Exception as e:
            logger.error(f"Failed to start effect {effect_class.__name__}: {e}")
            raise
    
    def stop_effect(self) -> None:
        """Stop the currently running effect."""
        if self._current_effect is not None:
            logger.info(f"Stopping effect {self._current_effect.__class__.__name__}")
            
            try:
                self._current_effect.stop()
                self._current_effect = None
                self._effect_parameters = {}
            except Exception as e:
                logger.error(f"Failed to stop effect: {e}")
                raise
    
    def get_effect_info(self) -> Dict[str, Any]:
        """
        Get information about the currently running effect.
        
        Returns:
            A dictionary containing information about the currently running effect
        """
        if self._current_effect is None:
            return {"running": False}
        
        # Get start time as datetime object
        start_time = getattr(self._current_effect, "start_time", None)
        
        # Convert datetime to ISO format string if it exists
        start_time_str = start_time.isoformat() if start_time else None
        
        return {
            "running": True,
            "name": self._current_effect.__class__.__name__,
            "description": self._current_effect.__class__.__doc__,
            "parameters": self._effect_parameters,
            "start_time": start_time_str,
            "runtime": getattr(self._current_effect, "runtime", None),
        }
    
    def shutdown(self) -> None:
        """
        Shutdown the LED manager.
        
        This method stops any running effects and turns off all LEDs.
        """
        logger.info("Shutting down LED manager")
        
        # Stop any running effect
        self.stop_effect()
        
        # Turn off all LEDs
        self._controller.clear()