from typing import Any

from pydantic import BaseModel, Field
from pydantic_extra_types.color import Color


class PresetSummary(BaseModel):
    name: str
    description: str


class PresetsListResponse(BaseModel):
    presets: list[PresetSummary]


class PresetInfo(BaseModel):
    description: str
    args: list[dict[str, Any]]


class RunningPresetResponse(BaseModel):
    name: str
    description: str
    start_time: str
    duration_seconds: float


class PresetStartRequest(BaseModel):
    preset_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    status: str
    preset: str | None = None


class ColorRequest(BaseModel):
    color: Color


class BrightnessRequest(BaseModel):
    brightness: float = Field(..., ge=0.0, le=1.0)
