from fastapi import APIRouter, Depends

from lib.api.dependencies import get_effect_service
from lib.api.routers.effects import running_info
from lib.api.routers.leds import color_hex
from lib.api.schemas import StateResponse
from lib.services.effect import EffectService

router = APIRouter(tags=["state"])


@router.get("/state", response_model=StateResponse)
def get_state(service: EffectService = Depends(get_effect_service)):
    """One-request strip summary: the running effect, brightness, solid
    color, and whether anything is lit — everything a status client needs
    without dragging the pixel buffer over the wire (that stays on /leds
    and /ws)."""
    pixels, brightness, color = service.controller.snapshot_with_color()
    return StateResponse(
        running=running_info(service),
        count=len(pixels),
        brightness=brightness,
        color=color_hex(color),
        lit=any(p != (0, 0, 0) for p in pixels),
    )
