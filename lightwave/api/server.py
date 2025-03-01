"""
API server for LightWave-Server.

This module provides a FastAPI-based HTTP API for controlling the LED strip.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from fastapi import FastAPI, HTTPException, Depends, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_extra_types.color import Color

from lightwave.config import settings
from lightwave.utils import get_logger, normalize_color, ColorType
from lightwave.controller import LEDManager
from lightwave.effects import EffectRegistry, Effect
from lightwave.api.models import (
    ErrorResponse,
    ColorRequest,
    BrightnessRequest,
    EffectInfo,
    EffectDetailedInfo,
    EffectsListResponse,
    EffectStartRequest,
    EffectStatusResponse,
)

logger = get_logger(__name__)


class LightWaveAPI:
    """
    LightWave API server.
    
    This class provides the FastAPI server for controlling the LED strip.
    """
    
    def __init__(
        self,
        led_manager: LEDManager,
        effect_registry: EffectRegistry
    ):
        """
        Initialize the API server.
        
        Args:
            led_manager: The LED manager to use
            effect_registry: The effect registry to use
        """
        logger.info("Initializing LightWave API server")
        
        self.led_manager = led_manager
        self.effect_registry = effect_registry
        
        # Initialize FastAPI
        self.app = FastAPI(
            title="LightWave API",
            description="API for controlling WS281X LED strips",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        
        # Set up CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.server.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Set up exception handlers
        self.app.add_exception_handler(HTTPException, self._http_exception_handler)
        self.app.add_exception_handler(Exception, self._general_exception_handler)
        
        # Set up shutdown event
        self.app.add_event_handler("shutdown", self._shutdown_event)
        
        # Register routes
        self._register_routes()
        
        logger.debug("LightWave API server initialized successfully")
    
    def _register_routes(self):
        """Register API routes."""
        # Effects routes
        self.app.get(
            "/api/effects",
            response_model=EffectsListResponse,
            tags=["effects"],
            summary="Get all available effects"
        )(self.get_effects)
        
        self.app.get(
            "/api/effects/{name}",
            response_model=EffectDetailedInfo,
            tags=["effects"],
            summary="Get detailed information about an effect"
        )(self.get_effect_info)
        
        self.app.get(
            "/api/status",
            response_model=EffectStatusResponse,
            tags=["effects"],
            summary="Get the status of the currently running effect"
        )(self.get_effect_status)
        
        self.app.post(
            "/api/effects/start",
            response_model=None,
            tags=["effects"],
            summary="Start an effect"
        )(self.start_effect)
        
        self.app.post(
            "/api/effects/stop",
            response_model=None,
            tags=["effects"],
            summary="Stop the currently running effect"
        )(self.stop_effect)
        
        # LED control routes
        self.app.post(
            "/api/leds/color",
            response_model=None,
            tags=["leds"],
            summary="Set the color of all LEDs"
        )(self.set_color)
        
        self.app.post(
            "/api/leds/brightness",
            response_model=None,
            tags=["leds"],
            summary="Set the brightness of all LEDs"
        )(self.set_brightness)
        
        self.app.post(
            "/api/leds/clear",
            response_model=None,
            tags=["leds"],
            summary="Turn off all LEDs"
        )(self.clear_leds)
    
    async def _http_exception_handler(self, request, exc):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP exception: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail)},
        )
    
    async def _general_exception_handler(self, request, exc):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    
    async def _shutdown_event(self):
        """Handle shutdown event."""
        logger.info("Shutting down API server")
        self.led_manager.shutdown()
    
    # ---- Effects routes ----
    
    async def get_effects(self):
        """
        Get all available effects.
        
        Returns:
            A list of all available effects
        """
        logger.debug("Getting all available effects")
        
        effects = []
        for name in self.effect_registry.get_effect_names():
            try:
                info = self.effect_registry.get_effect_info(name)
                effects.append(EffectInfo(
                    name=info["name"],
                    description=info["description"],
                ))
            except Exception as e:
                logger.error(f"Failed to get info for effect {name}: {e}")
        
        return {"effects": effects}
    
    async def get_effect_info(self, name: str = Path(..., description="Effect name")):
        """
        Get detailed information about an effect.
        
        Args:
            name: The name of the effect
            
        Returns:
            Detailed information about the effect
        """
        logger.debug(f"Getting info for effect {name}")
        
        if not self.effect_registry.has_effect(name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Effect {name} not found",
            )
        
        try:
            info = self.effect_registry.get_effect_info(name)
            return EffectDetailedInfo(
                name=info["name"],
                description=info["description"],
                parameters=info["parameters"],
            )
        except Exception as e:
            logger.error(f"Failed to get info for effect {name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get info for effect {name}",
            )
    
    async def get_effect_status(self):
        """
        Get the status of the currently running effect.
        
        Returns:
            The status of the currently running effect
        """
        logger.debug("Getting effect status")
        
        info = self.led_manager.get_effect_info()
        return EffectStatusResponse(**info)
    
    async def start_effect(self, request: EffectStartRequest):
        """
        Start an effect.
        
        Args:
            request: The effect start request
        """
        logger.debug(f"Starting effect {request.name} with parameters {request.parameters}")
        
        if not self.effect_registry.has_effect(request.name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Effect {request.name} not found",
            )
        
        try:
            effect_class = self.effect_registry.get_effect(request.name)
            self.led_manager.start_effect(effect_class, request.parameters)
        except ValueError as e:
            logger.error(f"Failed to start effect {request.name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            logger.error(f"Failed to start effect {request.name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start effect {request.name}",
            )
    
    async def stop_effect(self):
        """Stop the currently running effect."""
        logger.debug("Stopping effect")
        
        if not self.led_manager.current_effect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No effect running",
            )
        
        try:
            self.led_manager.stop_effect()
        except Exception as e:
            logger.error(f"Failed to stop effect: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop effect",
            )
    
    # ---- LED control routes ----
    
    async def set_color(self, request: ColorRequest):
        """
        Set the color of all LEDs.
        
        Args:
            request: The color request
        """
        logger.debug(f"Setting color to {request.color.as_rgb_tuple()}")
        
        try:
            self.led_manager.set_color(request.color.as_rgb_tuple())
        except Exception as e:
            logger.error(f"Failed to set color: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set color",
            )
    
    async def set_brightness(self, request: BrightnessRequest):
        """
        Set the brightness of all LEDs.
        
        Args:
            request: The brightness request
        """
        logger.debug(f"Setting brightness to {request.brightness}")
        
        try:
            self.led_manager.set_brightness(request.brightness)
        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set brightness",
            )
    
    async def clear_leds(self):
        """Turn off all LEDs."""
        logger.debug("Clearing LEDs")
        
        try:
            self.led_manager.clear()
        except Exception as e:
            logger.error(f"Failed to clear LEDs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear LEDs",
            )


def create_app():
    """
    Create the FastAPI application.
    
    Returns:
        The FastAPI application
    """
    logger.info("Creating FastAPI application")
    
    # Initialize components
    led_manager = LEDManager()
    effect_registry = EffectRegistry()
    
    # Create the API server
    api = LightWaveAPI(led_manager, effect_registry)
    
    return api.app