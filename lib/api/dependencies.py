from fastapi import Depends, HTTPException, Request

from lib.services.effect import EffectService


def get_effect_service(request: Request) -> EffectService:
    return request.app.state.effect_service


def require_idle(
    service: EffectService = Depends(get_effect_service),
) -> EffectService:
    """Guard for endpoints that mutate LED state directly — refuses if an
    effect is currently animating to avoid two writers fighting."""
    if service.is_busy():
        raise HTTPException(409, "A preset is currently running")

    return service
