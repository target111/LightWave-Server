import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lib.api.routers import leds, presets
from lib.config import Settings, build_driver
from lib.drivers.controller import LEDController
from lib.effects.registry import EffectRegistry
from lib.services.effect import EffectService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    driver = build_driver(settings)
    controller = LEDController(driver)
    registry = EffectRegistry()
    service = EffectService(controller, registry)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.effect_service = service
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
            await service.shutdown()

    app = FastAPI(title="LightWave", version="1.0.0", lifespan=lifespan)
    app.include_router(presets.router)
    app.include_router(leds.router)
    return app
