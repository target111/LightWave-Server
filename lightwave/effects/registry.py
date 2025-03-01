"""
Effect registry for LightWave-Server.

This module provides a registry for discovering and managing LED effects.
"""

import importlib
import inspect
import os
import pkgutil
import sys
from typing import Dict, List, Optional, Type, Any, Union

from lightwave.config import settings
from lightwave.utils import get_logger
from lightwave.effects.base import Effect, ParameterSpec

logger = get_logger(__name__)


class EffectRegistry:
    """
    Registry for discovering and managing LED effects.
    
    This class provides methods for discovering, registering, and retrieving
    effects from the effects module and custom directories.
    """
    
    def __init__(self, effects_path: str = settings.effect.effects_path):
        """
        Initialize the effect registry.
        
        Args:
            effects_path: The path to the effects directory
        """
        logger.info("Initializing effect registry")
        
        self._effects: Dict[str, Type[Effect]] = {}
        self._effects_path = effects_path
        
        # Discover effects
        self.discover_effects()
        
        logger.info(f"Discovered {len(self._effects)} effects")
    
    def discover_effects(self) -> None:
        """
        Discover effects from the effects module and custom directories.
        
        This method searches for effect classes in the effects module and
        custom directories, and registers them in the registry.
        """
        logger.debug(f"Discovering effects in {self._effects_path}")
        
        # Import all modules in the effects package
        package_name = self._effects_path.replace("/", ".")
        
        try:
            # Try to import the package
            package = importlib.import_module(package_name)
            
            # Loop through all modules in the package
            for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                if not is_pkg:
                    try:
                        # Import the module
                        module = importlib.import_module(name)
                        
                        # Loop through all classes in the module
                        for _, obj in inspect.getmembers(module, inspect.isclass):
                            # Register the effect if it's a subclass of Effect
                            if issubclass(obj, Effect) and obj != Effect:
                                self.register_effect(obj)
                    except Exception as e:
                        logger.error(f"Failed to import module {name}: {e}")
        except Exception as e:
            logger.error(f"Failed to import package {package_name}: {e}")
    
    def register_effect(self, effect_class: Type[Effect]) -> None:
        """
        Register an effect in the registry.
        
        Args:
            effect_class: The effect class to register
        """
        name = effect_class.__name__
        logger.debug(f"Registering effect {name}")
        self._effects[name] = effect_class
    
    def get_effect(self, name: str) -> Optional[Type[Effect]]:
        """
        Get an effect by name.
        
        Args:
            name: The name of the effect
            
        Returns:
            The effect class, or None if not found
        """
        return self._effects.get(name)
    
    def get_all_effects(self) -> Dict[str, Type[Effect]]:
        """
        Get all registered effects.
        
        Returns:
            A dictionary of effect names to effect classes
        """
        return self._effects.copy()
    
    def get_effect_names(self) -> List[str]:
        """
        Get the names of all registered effects.
        
        Returns:
            A list of effect names
        """
        return list(self._effects.keys())
    
    def get_effect_info(self, name: str) -> Dict[str, Any]:
        """
        Get information about an effect.
        
        Args:
            name: The name of the effect
            
        Returns:
            A dictionary containing information about the effect
            
        Raises:
            KeyError: If the effect is not found
        """
        effect_class = self.get_effect(name)
        if effect_class is None:
            raise KeyError(f"Effect {name} not found")
        
        # Get docstring and parameters
        docstring = effect_class.__doc__ or "No description available"
        parameters = [
            {
                "name": param.name,
                "type": param.type.value,
                "description": param.description,
                "default": param.default,
                "min_value": param.min_value,
                "max_value": param.max_value,
                "options": param.options,
            }
            for param in effect_class.parameters
        ]
        
        return {
            "name": name,
            "description": docstring,
            "parameters": parameters,
        }
    
    def has_effect(self, name: str) -> bool:
        """
        Check if an effect exists.
        
        Args:
            name: The name of the effect
            
        Returns:
            True if the effect exists, False otherwise
        """
        return name in self._effects