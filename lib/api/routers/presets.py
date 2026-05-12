import datetime

from fastapi import APIRouter, Depends, HTTPException

from lib.api.dependencies import get_effect_service
from lib.api.schemas import (
    PresetInfo,
    PresetsListResponse,
    PresetStartRequest,
    PresetSummary,
    RunningPresetResponse,
    StatusResponse,
)
from lib.services.effect import (
    EffectService,
    EffectStartError,
    NoEffectRunningError,
)

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=PresetsListResponse)
def list_presets(service: EffectService = Depends(get_effect_service)):
    reg = service.registry
    return PresetsListResponse(
        presets=[
            PresetSummary(name=n, description=reg.describe(n))
            for n in reg.names()
        ]
    )


@router.get("/running", response_model=RunningPresetResponse)
def get_running(service: EffectService = Depends(get_effect_service)):
    eff = service.running
    if eff is None or not eff.is_alive():
        raise HTTPException(404, "No preset running")

    return RunningPresetResponse(
        name=eff.__class__.__name__,
        description=service.registry.describe(eff.__class__.__name__),
        start_time=eff.start_time.isoformat(),
        duration_seconds=(
            datetime.datetime.now() - eff.start_time
        ).total_seconds(),
    )


@router.get("/{preset_name}", response_model=PresetInfo)
def get_preset(
    preset_name: str,
    service: EffectService = Depends(get_effect_service),
):
    if not service.registry.has(preset_name):
        raise HTTPException(404, "Preset not found")
    return PresetInfo(
        description=service.registry.describe(preset_name),
        args=service.registry.schema(preset_name),
    )


@router.post("/start", response_model=StatusResponse, status_code=202)
async def start_preset(
    body: PresetStartRequest,
    service: EffectService = Depends(get_effect_service),
):
    try:
        await service.start(body.preset_name, body.args)
    except KeyError:
        raise HTTPException(404, "Preset not found")
    except EffectStartError as e:
        raise HTTPException(503, f"Failed to start preset: {e}")
    return StatusResponse(status="started", preset=body.preset_name)


@router.post("/stop", response_model=StatusResponse, status_code=202)
async def stop_preset(service: EffectService = Depends(get_effect_service)):
    try:
        await service.stop()
    except NoEffectRunningError:
        raise HTTPException(404, "No preset running")

    return StatusResponse(status="stopped")
