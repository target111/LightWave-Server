from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from lib.services.effect import EffectStartError
from lib.services.presets import PresetError, PresetNotFoundError


def _detail(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions to HTTP responses in one place, so route
    handlers can let them propagate instead of repeating the same
    try/except → HTTPException. Context-dependent mappings (e.g. an
    unknown effect name meaning 404 when named directly but 422 when it
    is a stale preset reference) stay in the handlers that own them."""

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        # FastAPI's default detail is a list of error objects while every
        # other error here is a string; flatten so clients can always
        # print `detail` as-is.
        parts = []
        for err in exc.errors():
            loc = ".".join(
                str(p) for p in err.get("loc", ()) if p != "body"
            )
            msg = err.get("msg", "invalid value")
            parts.append(f"{loc}: {msg}" if loc else msg)
        return _detail(422, "; ".join(parts) or "invalid request")

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
