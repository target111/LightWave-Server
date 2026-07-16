import datetime

from fastapi import APIRouter, Depends, HTTPException

from lib.api.dependencies import get_effect_service
from lib.api.schemas import (
    EffectInfo,
    EffectsListResponse,
    EffectSummary,
    RunningEffectInfo,
    RunningResponse,
    StartRequest,
    StartResponse,
    StopResponse,
)
from lib.services.effect import EffectService

router = APIRouter(prefix="/effects", tags=["effects"])


def running_info(service: EffectService) -> RunningEffectInfo | None:
    """The running effect as clients see it, or None when idle. Shared
    with the /state summary endpoint."""
    eff = service.running
    if eff is None:
        return None
    name = eff.NAME
    now = datetime.datetime.now(datetime.UTC)
    return RunningEffectInfo(
        name=name,
        description=service.registry.describe(name),
        preset=service.running_preset,
        start_time=eff.start_time,
        duration_seconds=(now - eff.start_time).total_seconds(),
    )


@router.get("", response_model=EffectsListResponse)
def list_effects(service: EffectService = Depends(get_effect_service)):
    reg = service.registry
    return EffectsListResponse(
        effects=[
            EffectSummary(name=n, description=reg.describe(n))
            for n in reg.names()
        ]
    )


# Declared before /{effect_name} so the literal path wins; "running" and
# "stop" are therefore reserved effect names.
@router.get("/running", response_model=RunningResponse)
def get_running(service: EffectService = Depends(get_effect_service)):
    return RunningResponse(running=running_info(service))


@router.post("/stop", response_model=StopResponse)
async def stop_effect(service: EffectService = Depends(get_effect_service)):
    was_running = await service.stop()
    return StopResponse(was_running=was_running)


# exclude_none: an option's min/max/choices are omitted when it doesn't
# declare them, not sent as null.
@router.get(
    "/{effect_name}",
    response_model=EffectInfo,
    response_model_exclude_none=True,
)
def get_effect(
    effect_name: str,
    service: EffectService = Depends(get_effect_service),
):
    if not service.registry.has(effect_name):
        raise HTTPException(404, "Effect not found")
    return EffectInfo(
        description=service.registry.describe(effect_name),
        args=service.registry.schema(effect_name),
    )


@router.post("/{effect_name}/start", response_model=StartResponse)
async def start_effect(
    effect_name: str,
    body: StartRequest | None = None,
    service: EffectService = Depends(get_effect_service),
):
    args = (body or StartRequest()).args
    try:
        await service.start(effect_name, args)
    except KeyError:
        raise HTTPException(404, "Effect not found")
    return StartResponse(effect=effect_name)
