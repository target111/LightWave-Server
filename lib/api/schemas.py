from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_extra_types.color import Color


class EffectSummary(BaseModel):
    name: str
    description: str


class EffectsListResponse(BaseModel):
    effects: list[EffectSummary]


class EffectInfo(BaseModel):
    description: str
    args: list[dict[str, Any]]


class RunningEffectResponse(BaseModel):
    name: str
    description: str
    # Name of the preset the effect was started from, if any.
    preset: str | None = None
    start_time: str
    duration_seconds: float


class EffectStartRequest(BaseModel):
    effect_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    status: Literal["started", "stopped"]
    effect: str | None = None
    preset: str | None = None


class LedStateResponse(BaseModel):
    count: int
    brightness: float
    pixels: list[tuple[int, int, int]]


class PresetBody(BaseModel):
    """Client-supplied part of a preset; the name comes from the URL."""

    effect: str
    args: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class PresetRecord(PresetBody):
    name: str


class PresetsListResponse(BaseModel):
    presets: list[PresetRecord]


class ColorRequest(BaseModel):
    color: Color


class BrightnessRequest(BaseModel):
    brightness: float = Field(..., ge=0.0, le=1.0)
