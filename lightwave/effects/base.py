"""
Base classes for LED effects.

This module provides base classes for implementing LED effects.
"""

import abc
import datetime
import threading
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union, Callable, TypeVar, cast

from lightwave.config import settings
from lightwave.utils import get_logger, ColorType, ColorValue

logger = get_logger(__name__)


class ParameterType(str, Enum):
    """Parameter types for effect parameters."""
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    COLOR = "color"
    STRING = "string"
    ENUM = "enum"


@dataclass
class ParameterSpec:
    """
    Specification for an effect parameter.
    
    This class defines the metadata for an effect parameter, including
    its type, range, description, and default value.
    """
    name: str
    type: ParameterType
    description: str
    default: Any
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    options: Optional[List[str]] = None
    
    def validate(self, value: Any) -> Any:
        """
        Validate a parameter value against this specification.
        
        Args:
            value: The parameter value to validate
            
        Returns:
            The validated parameter value, possibly converted to the correct type
            
        Raises:
            ValueError: If the parameter value is invalid
        """
        # Check if value is None, use default if so
        if value is None:
            return self.default
        
        # Validate based on parameter type
        if self.type == ParameterType.INT:
            if not isinstance(value, int):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Parameter {self.name} must be an integer")
            
            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"Parameter {self.name} must be >= {self.min_value}")
            
            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"Parameter {self.name} must be <= {self.max_value}")
        
        elif self.type == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Parameter {self.name} must be a number")
            
            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"Parameter {self.name} must be >= {self.min_value}")
            
            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"Parameter {self.name} must be <= {self.max_value}")
        
        elif self.type == ParameterType.BOOL:
            if isinstance(value, str):
                value = value.lower() == "true"
            else:
                try:
                    value = bool(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Parameter {self.name} must be a boolean")
        
        elif self.type == ParameterType.COLOR:
            from lightwave.utils.color import normalize_color
            try:
                value = normalize_color(value)
            except (ValueError, TypeError):
                raise ValueError(f"Parameter {self.name} must be a valid color")
        
        elif self.type == ParameterType.STRING:
            try:
                value = str(value)
            except (ValueError, TypeError):
                raise ValueError(f"Parameter {self.name} must be a string")
        
        elif self.type == ParameterType.ENUM:
            if self.options is None:
                raise ValueError(f"Parameter {self.name} is an enum but has no options")
            
            try:
                value = str(value)
            except (ValueError, TypeError):
                raise ValueError(f"Parameter {self.name} must be a string")
            
            if value not in self.options:
                raise ValueError(f"Parameter {self.name} must be one of {self.options}")
        
        return value


class Effect(abc.ABC, threading.Thread):
    """
    Base class for LED effects.
    
    This class provides the foundation for implementing LED effects that
    run in a separate thread.
    """
    
    # Parameter specifications
    parameters: List[ParameterSpec] = []
    
    def __init__(self, controller, **kwargs):
        """
        Initialize the effect.
        
        Args:
            controller: The LED controller to use
            **kwargs: Effect-specific parameters
        """
        super().__init__(daemon=True)
        self.controller = controller
        
        # Event to signal the thread to stop
        self._stop_event = threading.Event()
        
        # Event to signal a parameter update
        self._update_event = threading.Event()
        
        # Store start time and frame metrics
        self.start_time = None
        self._frame_count = 0
        self._last_frame_time = None
        self._fps = settings.effect.default_fps
        
        # Validate and store parameters
        self.validate_parameters(**kwargs)
        
        logger.debug(f"Initialized {self.__class__.__name__} effect")
    
    def validate_parameters(self, **kwargs):
        """
        Validate effect parameters against the specifications.
        
        Args:
            **kwargs: Effect-specific parameters
            
        Raises:
            ValueError: If any parameter is invalid
        """
        self._parameters = {}
        
        # Create a dictionary of parameter specs for easier lookup
        param_specs = {param.name: param for param in self.parameters}
        
        # Process each parameter
        for name, value in kwargs.items():
            if name in param_specs:
                self._parameters[name] = param_specs[name].validate(value)
            else:
                logger.warning(f"Unknown parameter {name} for {self.__class__.__name__} effect")
        
        # Add defaults for missing parameters
        for name, spec in param_specs.items():
            if name not in self._parameters:
                self._parameters[name] = spec.default
    
    def update_parameters(self, **kwargs):
        """
        Update effect parameters while the effect is running.
        
        Args:
            **kwargs: Updated effect-specific parameters
            
        Raises:
            ValueError: If any parameter is invalid
        """
        logger.debug(f"Updating parameters for {self.__class__.__name__} effect: {kwargs}")
        
        # Validate and update parameters
        self.validate_parameters(**{**self._parameters, **kwargs})
        
        # Signal the thread to update
        self._update_event.set()
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """
        Get a parameter value.
        
        Args:
            name: The name of the parameter
            default: The default value to return if the parameter is not set
            
        Returns:
            The parameter value
        """
        return self._parameters.get(name, default)
    
    def run(self):
        """
        Run the effect.
        
        This method is called when the thread is started. It runs the effect
        until the stop event is set.
        """
        logger.info(f"Starting {self.__class__.__name__} effect")
        
        # Store start time
        self.start_time = datetime.datetime.now()
        
        # Run until stopped
        while not self._stop_event.is_set():
            # Record frame start time
            frame_start = time.time()
            
            # Render frame
            self.render_frame()
            
            # Update frame metrics
            self._frame_count += 1
            self._last_frame_time = time.time()
            
            # Calculate time to sleep
            elapsed = time.time() - frame_start
            sleep_time = max(0, 1 / self._fps - elapsed)
            
            # Sleep for the remaining time
            time.sleep(sleep_time)
            
            # Reset the update event
            self._update_event.clear()
        
        logger.info(f"Stopping {self.__class__.__name__} effect")
    
    def stop(self):
        """Stop the effect."""
        logger.info(f"Stopping {self.__class__.__name__} effect")
        self._stop_event.set()
        self.join(timeout=2)
        
        # Turn off all LEDs
        self.controller.clear()
    
    @property
    def runtime(self) -> Optional[float]:
        """
        Get the runtime of the effect in seconds.
        
        Returns:
            The runtime in seconds, or None if the effect has not been started
        """
        if self.start_time is None:
            return None
        
        return (datetime.datetime.now() - self.start_time).total_seconds()
    
    @property
    def fps(self) -> float:
        """
        Get the current frames per second.
        
        Returns:
            The current frames per second
        """
        return self._fps
    
    @fps.setter
    def fps(self, value: float) -> None:
        """
        Set the frames per second.
        
        Args:
            value: The frames per second
            
        Raises:
            ValueError: If the value is not positive or exceeds the maximum
        """
        if value <= 0:
            raise ValueError("FPS must be positive")
        
        if value > settings.effect.max_fps:
            raise ValueError(f"FPS cannot exceed {settings.effect.max_fps}")
        
        self._fps = value
    
    @abc.abstractmethod
    def render_frame(self) -> None:
        """
        Render a single frame of the effect.
        
        This method must be implemented by subclasses to render a single
        frame of the effect.
        """
        pass