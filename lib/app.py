import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from lib.api.broadcast import FrameBroadcaster
from lib.api.routers import leds, presets, ws
from lib.config import Settings, build_driver
from lib.drivers.controller import LEDController
from lib.effects.registry import EffectRegistry
from lib.services.effect import EffectService

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    driver = build_driver(settings)
    controller = LEDController(driver)
    registry = EffectRegistry()
    service = EffectService(controller, registry)
    broadcaster = FrameBroadcaster(service, fps=settings.broadcast_fps)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.effect_service = service
        app.state.broadcaster = broadcaster
        # Both change signals feed the same fan-out: pixel writes and
        # preset lifecycle transitions wake the broadcaster.
        controller.on_change = broadcaster.notify
        service.on_state_change = broadcaster.notify
        broadcaster.start()
        logger.info(
            "LightWave starting (backend=%s, pin=%s, count=%d)",
            settings.backend,
            settings.led_pin,
            settings.led_count,
        )
        try:
            yield
        finally:
            logger.info("LightWave shutting down")
            await broadcaster.stop()
            controller.on_change = None
            service.on_state_change = None
            await service.shutdown()

    app = FastAPI(title="LightWave", version="1.0.0", lifespan=lifespan)
    app.include_router(presets.router)
    app.include_router(leds.router)
    app.include_router(ws.router)
    # Mounted last so API routes win; html=True serves index.html at "/".
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
