import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_extra_types.color import Color


class EffectSummary(BaseModel):
    name: str
    description: str


class EffectsListResponse(BaseModel):
    effects: list[EffectSummary]


class OptionSchema(BaseModel):
    """One effect option as advertised to clients. Mirrors
    `Option.schema()` in lib/effects/base.py; `min`/`max`/`choices` are
    omitted from responses when an option doesn't declare them."""

    name: str
    type: Literal["int", "float", "bool", "color", "enum"]
    default: Any
    description: str
    min: float | None = None
    max: float | None = None
    choices: list[str] | None = None


class EffectInfo(BaseModel):
    description: str
    args: list[OptionSchema]


class RunningEffectInfo(BaseModel):
    name: str
    description: str
    # Name of the preset the effect was started from, if any.
    preset: str | None = None
    start_time: datetime.datetime
    duration_seconds: float


class RunningResponse(BaseModel):
    """`running` is null when the strip is idle — a normal state, not an
    error."""

    running: RunningEffectInfo | None


class StartRequest(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict)


class StartResponse(BaseModel):
    status: Literal["started"] = "started"
    effect: str
    preset: str | None = None


class StopResponse(BaseModel):
    status: Literal["stopped"] = "stopped"
    # False when nothing was running; stopping an idle strip is not an
    # error.
    was_running: bool


class LedStateResponse(BaseModel):
    count: int
    brightness: float
    # The solid color as "#rrggbb" when the strip was last set to one and
    # nothing has painted over it since; null when off or effect-driven.
    color: str | None
    pixels: list[tuple[int, int, int]]


class StateResponse(BaseModel):
    """Lightweight strip summary for status clients (bar widgets, CLI
    status): everything except the pixel buffer, in one request."""

    running: RunningEffectInfo | None
    count: int
    brightness: float
    color: str | None
    lit: bool


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
