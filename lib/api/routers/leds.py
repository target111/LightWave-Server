from fastapi import APIRouter, Depends, Response

from lib.api.dependencies import get_effect_service, require_idle
from lib.api.schemas import BrightnessRequest, ColorRequest, LedStateResponse
from lib.drivers.base import Color
from lib.services.effect import EffectService

router = APIRouter(prefix="/leds", tags=["leds"])


def color_hex(color: Color | None) -> str | None:
    """An RGB tuple as the "#rrggbb" form the API speaks, passing None
    through. Shared with the /state summary endpoint."""
    if color is None:
        return None
    r, g, b = color
    return f"#{r:02x}{g:02x}{b:02x}"


@router.get("", response_model=LedStateResponse)
def get_state(service: EffectService = Depends(get_effect_service)):
    pixels, brightness, color = service.controller.snapshot_with_color()
    return LedStateResponse(
        count=service.controller.count,
        brightness=brightness,
        color=color_hex(color),
        pixels=pixels,
    )


@router.put("/color", status_code=204, response_class=Response)
def set_color(
    body: ColorRequest, service: EffectService = Depends(require_idle)
):
    rgb = body.color.as_rgb_tuple()[:3]
    service.controller.set_color(rgb)


@router.delete("/color", status_code=204, response_class=Response)
def clear(service: EffectService = Depends(require_idle)):
    service.controller.clear()


@router.put("/brightness", status_code=204, response_class=Response)
def set_brightness(
    body: BrightnessRequest,
    service: EffectService = Depends(get_effect_service),
):
    service.controller.set_brightness(body.brightness)
