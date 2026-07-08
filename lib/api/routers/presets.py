from fastapi import APIRouter, Depends, HTTPException, Response

from lib.api.dependencies import get_effect_service, get_preset_store
from lib.api.schemas import (
    PresetBody,
    PresetRecord,
    PresetsListResponse,
    StatusResponse,
)
from lib.services.effect import EffectService, EffectStartError
from lib.services.presets import (
    PresetError,
    PresetNotFoundError,
    PresetStore,
)

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=PresetsListResponse)
def list_presets(store: PresetStore = Depends(get_preset_store)):
    return PresetsListResponse(
        presets=[PresetRecord(**p) for p in store.list()]
    )


@router.get("/{name}", response_model=PresetRecord)
def get_preset(name: str, store: PresetStore = Depends(get_preset_store)):
    try:
        return store.get(name)
    except PresetNotFoundError:
        raise HTTPException(404, "Preset not found")


@router.put("/{name}", response_model=PresetRecord)
def save_preset(
    name: str,
    body: PresetBody,
    store: PresetStore = Depends(get_preset_store),
):
    try:
        return store.save(name, body.effect, body.args, body.description)
    except PresetError as e:
        raise HTTPException(422, str(e))


@router.delete("/{name}", status_code=204, response_class=Response)
def delete_preset(name: str, store: PresetStore = Depends(get_preset_store)):
    try:
        store.delete(name)
    except PresetNotFoundError:
        raise HTTPException(404, "Preset not found")


@router.post("/{name}/start", response_model=StatusResponse, status_code=202)
async def start_preset(
    name: str,
    store: PresetStore = Depends(get_preset_store),
    service: EffectService = Depends(get_effect_service),
):
    try:
        preset = store.get(name)
    except PresetNotFoundError:
        raise HTTPException(404, "Preset not found")

    try:
        await service.start(preset["effect"], preset["args"], preset=name)
    except KeyError:
        # The preset outlived its effect (renamed/removed from the library).
        raise HTTPException(
            422, f"Effect {preset['effect']!r} no longer exists"
        )
    except EffectStartError as e:
        raise HTTPException(503, f"Failed to start preset: {e}")
    return StatusResponse(
        status="started", effect=preset["effect"], preset=name
    )
