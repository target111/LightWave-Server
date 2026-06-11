from fastapi import APIRouter, Depends, Response

from lib.api.dependencies import get_effect_service, require_idle
from lib.api.schemas import BrightnessRequest, ColorRequest
from lib.services.effect import EffectService

router = APIRouter(prefix="/leds", tags=["leds"])


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
