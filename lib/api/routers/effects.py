import datetime

from fastapi import APIRouter, Depends, HTTPException

from lib.api.dependencies import get_effect_service
from lib.api.schemas import (
    EffectInfo,
    EffectsListResponse,
    EffectStartRequest,
    EffectSummary,
    RunningEffectResponse,
    StatusResponse,
)
from lib.services.effect import EffectService

router = APIRouter(prefix="/effects", tags=["effects"])


@router.get("", response_model=EffectsListResponse)
def list_effects(service: EffectService = Depends(get_effect_service)):
    reg = service.registry
    return EffectsListResponse(
        effects=[
            EffectSummary(name=n, description=reg.describe(n))
            for n in reg.names()
        ]
    )


@router.get("/running", response_model=RunningEffectResponse)
def get_running(service: EffectService = Depends(get_effect_service)):
    eff = service.running
    if eff is None:
        raise HTTPException(404, "No effect running")

    name = eff.__class__.__name__
    return RunningEffectResponse(
        name=name,
        description=service.registry.describe(name),
        preset=service.running_preset,
        start_time=eff.start_time.isoformat(),
        duration_seconds=(
            datetime.datetime.now() - eff.start_time
        ).total_seconds(),
    )


@router.get("/{effect_name}", response_model=EffectInfo)
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


@router.post("/start", response_model=StatusResponse, status_code=202)
async def start_effect(
    body: EffectStartRequest,
    service: EffectService = Depends(get_effect_service),
):
    try:
        await service.start(body.effect_name, body.args)
    except KeyError:
        raise HTTPException(404, "Effect not found")
    return StatusResponse(status="started", effect=body.effect_name)


@router.post("/stop", response_model=StatusResponse, status_code=202)
async def stop_effect(service: EffectService = Depends(get_effect_service)):
    await service.stop()
    return StatusResponse(status="stopped")
