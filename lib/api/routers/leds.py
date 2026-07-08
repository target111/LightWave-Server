from fastapi import APIRouter, Depends, Response

from lib.api.dependencies import get_effect_service, require_idle
from lib.api.schemas import BrightnessRequest, ColorRequest, LedStateResponse
from lib.services.effect import EffectService

router = APIRouter(prefix="/leds", tags=["leds"])


@router.get("", response_model=LedStateResponse)
def get_state(service: EffectService = Depends(get_effect_service)):
    pixels, brightness = service.controller.snapshot()
    return LedStateResponse(
        count=service.controller.count,
        brightness=brightness,
        pixels=pixels,
    )


@router.post("/color/set", status_code=204, response_class=Response)
def set_color(
    body: ColorRequest, service: EffectService = Depends(require_idle)
):
    rgb = body.color.as_rgb_tuple()[:3]
    service.controller.set_color(rgb)


@router.post("/color/clear", status_code=204, response_class=Response)
def clear(service: EffectService = Depends(require_idle)):
    service.controller.clear()


@router.post("/brightness", status_code=204, response_class=Response)
def set_brightness(
    body: BrightnessRequest,
    service: EffectService = Depends(get_effect_service),
):
    service.controller.set_brightness(body.brightness)
