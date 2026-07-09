from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from lib.services.effect import EffectStartError, NoEffectRunningError
from lib.services.presets import PresetError, PresetNotFoundError


def _detail(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions to HTTP responses in one place, so route
    handlers can let them propagate instead of repeating the same
    try/except → HTTPException. Context-dependent mappings (e.g. an
    unknown effect name meaning 404 when named directly but 422 when it
    is a stale preset reference) stay in the handlers that own them."""

    @app.exception_handler(NoEffectRunningError)
    async def _no_effect(request: Request, exc: NoEffectRunningError):
        return _detail(404, "No effect running")

    @app.exception_handler(PresetNotFoundError)
    async def _preset_missing(request: Request, exc: PresetNotFoundError):
        return _detail(404, "Preset not found")

    @app.exception_handler(PresetError)
    async def _preset_invalid(request: Request, exc: PresetError):
        # PresetError messages are written to be safe as the API detail.
        return _detail(422, str(exc))

    @app.exception_handler(EffectStartError)
    async def _effect_start_failed(request: Request, exc: EffectStartError):
        return _detail(503, f"Failed to start effect: {exc}")
