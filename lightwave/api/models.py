"""
API models for LightWave-Server.

This module provides Pydantic models for the API interface.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from pydantic_extra_types.color import Color


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str = Field(..., description="Error detail message")


class ColorRequest(BaseModel):
    """Color request model."""
    color: Color = Field(..., description="Color value in any valid format (hex, rgb, etc.)")


class BrightnessRequest(BaseModel):
    """Brightness request model."""
    brightness: float = Field(
        ...,
        description="Brightness value (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )


class EffectInfo(BaseModel):
    """Effect information model."""
    name: str = Field(..., description="Effect name")
    description: str = Field(..., description="Effect description")


class EffectParameter(BaseModel):
    """Effect parameter model."""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    default: Any = Field(..., description="Default parameter value")
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum value (for numeric types)")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum value (for numeric types)")
    options: Optional[List[str]] = Field(None, description="Available options (for enum types)")


class EffectDetailedInfo(BaseModel):
    """Detailed effect information model."""
    name: str = Field(..., description="Effect name")
    description: str = Field(..., description="Effect description")
    parameters: List[EffectParameter] = Field(default_factory=list, description="Effect parameters")


class EffectsListResponse(BaseModel):
    """Effects list response model."""
    effects: List[EffectInfo] = Field(default_factory=list, description="List of available effects")


class EffectStartRequest(BaseModel):
    """Effect start request model."""
    name: str = Field(..., description="Effect name")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Effect parameters")


class EffectStatusResponse(BaseModel):
    """Effect status response model."""
    running: bool = Field(..., description="Whether an effect is running")
    name: Optional[str] = Field(None, description="Running effect name")
    description: Optional[str] = Field(None, description="Running effect description")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Running effect parameters")
    start_time: Optional[str] = Field(None, description="Effect start time ISO format")
    runtime: Optional[float] = Field(None, description="Effect runtime in seconds")