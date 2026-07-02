import asyncio
import logging
from typing import Optional

from lib.drivers.controller import LEDController
from lib.effects.base import EffectBase
from lib.effects.registry import EffectRegistry

logger = logging.getLogger(__name__)


class NoEffectRunningError(Exception):
    pass


class EffectStartError(Exception):
    """Raised when an effect fails to construct (bad args, busy port...)."""


class EffectService:
    """Owns the currently running effect. All start/stop transitions go
    through one asyncio lock so two concurrent API calls cannot race."""

    FADE_DURATION = 0.5
    JOIN_TIMEOUT = 2.0

    def __init__(self, led: LEDController, registry: EffectRegistry):
        self._led = led
        self._registry = registry
        self._running: Optional[EffectBase] = None
        self._lock = asyncio.Lock()

    @property
    def controller(self) -> LEDController:
        return self._led

    @property
    def registry(self) -> EffectRegistry:
        return self._registry

    @property
    def running(self) -> Optional[EffectBase]:
        """The live effect, or None. An effect whose thread has exited
        (finished or crashed) counts as not running."""
        eff = self._running
        if eff is not None and eff.is_alive():
            return eff
        return None

    @property
    def running_name(self) -> Optional[str]:
        eff = self.running
        return None if eff is None else eff.__class__.__name__

    def is_busy(self) -> bool:
        return self.running is not None

    async def start(self, name: str, args: dict) -> EffectBase:
        if not self._registry.has(name):
            raise KeyError(name)
        cls = self._registry.get(name)
        async with self._lock:
            await self._stop_locked()
            self._led.set_brightness(1.0)
            try:
                effect = cls(self._led, **args)
            except Exception as e:
                logger.exception("Failed to construct effect %s", name)
                raise EffectStartError(str(e)) from e
            effect.start()
            self._running = effect
            logger.info("Started effect %s with args=%s", name, args)
            return effect

    async def stop(self) -> None:
        async with self._lock:
            if self._running is None:
                raise NoEffectRunningError()
            await self._stop_locked()

    async def shutdown(self) -> None:
        async with self._lock:
            await self._stop_locked()
            await asyncio.to_thread(self._led.close)

    async def _stop_locked(self) -> None:
        """Stop + join + fade. Caller must hold `self._lock`."""
        effect = self._running
        if effect is None:
            return
        self._running = None
        await asyncio.to_thread(self._teardown_blocking, effect)

    def _teardown_blocking(self, effect: EffectBase) -> None:
        effect.stop()
        effect.join(timeout=self.JOIN_TIMEOUT)
        if effect.is_alive():
            logger.warning(
                "Effect %s did not stop within %.1fs",
                effect.name,
                self.JOIN_TIMEOUT,
            )
        self._led.fade_out(self.FADE_DURATION)
