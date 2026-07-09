import asyncio
import functools
import logging
import time
from dataclasses import dataclass
from typing import Callable

from lib.drivers.controller import LEDController
from lib.effects.base import EffectBase
from lib.effects.registry import EffectRegistry

logger = logging.getLogger(__name__)


class NoEffectRunningError(Exception):
    pass


class EffectStartError(Exception):
    """Raised when an effect fails to construct (bad args, busy port...)."""


@dataclass(frozen=True)
class RunningEffect:
    """The live effect plus the preset it was started from (if any). Set
    and cleared as one reference so the effect and its provenance can't
    fall out of sync."""

    effect: EffectBase
    preset: str | None = None

    @property
    def is_live(self) -> bool:
        """False once run() has exited (finished or crashed) — `finished`
        flips before the thread is fully dead, so an effect that ended on
        its own reads as not-live even before it has been reaped."""
        return not self.effect.finished and self.effect.is_alive()


class EffectService:
    """Owns the currently running effect. All start/stop transitions go
    through one asyncio lock so two concurrent API calls cannot race."""

    FADE_DURATION = 0.5
    FADE_FPS = 30
    JOIN_TIMEOUT = 2.0

    def __init__(self, led: LEDController, registry: EffectRegistry):
        self._led = led
        self._registry = registry
        self._current: RunningEffect | None = None
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        # Called after the running effect changes: started, stopped, or
        # the effect thread exited on its own (finished/crashed). Must be
        # cheap and thread-safe — self-termination fires it from the
        # effect thread.
        self.on_state_change: Callable[[], None] | None = None

    def _notify_state(self) -> None:
        cb = self.on_state_change
        if cb is not None:
            cb()

    @property
    def controller(self) -> LEDController:
        return self._led

    @property
    def registry(self) -> EffectRegistry:
        return self._registry

    @property
    def _live(self) -> RunningEffect | None:
        """The current effect if it is still animating, else None — the
        single source both `running` and `running_preset` derive from, so
        they can never disagree about whether something is running."""
        cur = self._current
        return cur if cur is not None and cur.is_live else None

    @property
    def running(self) -> EffectBase | None:
        """The live effect, or None. An effect whose run() has exited
        (finished or crashed) counts as not running."""
        cur = self._live
        return cur.effect if cur is not None else None

    @property
    def running_name(self) -> str | None:
        eff = self.running
        return None if eff is None else eff.__class__.__name__

    @property
    def running_preset(self) -> str | None:
        """Name of the preset the live effect was started from, if any."""
        cur = self._live
        return cur.preset if cur is not None else None

    def is_busy(self) -> bool:
        return self.running is not None

    async def start(
        self, name: str, args: dict, preset: str | None = None
    ) -> EffectBase:
        cls = self._registry.get(name)  # raises KeyError for unknown names
        async with self._lock:
            self._loop = asyncio.get_running_loop()
            await self._stop_locked()
            self._led.set_brightness(1.0)
            try:
                effect = cls(self._led, **args)
            except Exception as e:
                logger.exception("Failed to construct effect %s", name)
                raise EffectStartError(str(e)) from e
            effect.on_finished = functools.partial(self._effect_exited, effect)
            effect.start()
            self._current = RunningEffect(effect, preset)
            self._notify_state()
            logger.info("Started effect %s with args=%s", name, args)
            return effect

    async def stop(self) -> None:
        async with self._lock:
            if self._current is None:
                raise NoEffectRunningError()
            await self._stop_locked()

    async def shutdown(self) -> None:
        async with self._lock:
            await self._stop_locked()
            await asyncio.to_thread(self._led.close)

    def _effect_exited(self, effect: EffectBase) -> None:
        """Runs on the effect thread whenever its run() exits. Pushes the
        state change right away and schedules the cleanup that needs the
        service lock back onto the event loop."""
        self._notify_state()
        loop = self._loop
        if loop is not None and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._reap(effect), loop)

    async def _reap(self, effect: EffectBase) -> None:
        """Tear down an effect that exited on its own (finished or
        crashed) so it converges on the same end state as an explicit
        stop(): `_current` cleared and the strip faded to black."""
        async with self._lock:
            cur = self._current
            if cur is None or cur.effect is not effect:
                return  # already stopped explicitly or replaced
            self._current = None
            await asyncio.to_thread(self._teardown_blocking, effect)
        self._notify_state()

    async def _stop_locked(self) -> None:
        """Stop + join + fade. Caller must hold `self._lock`."""
        cur = self._current
        if cur is None:
            return
        self._current = None
        await asyncio.to_thread(self._teardown_blocking, cur.effect)

    def _teardown_blocking(self, effect: EffectBase) -> None:
        effect.stop()
        effect.join(timeout=self.JOIN_TIMEOUT)
        if effect.is_alive():
            logger.warning(
                "Effect %s did not stop within %.1fs",
                effect.name,
                self.JOIN_TIMEOUT,
            )
        self._fade_out(self.FADE_DURATION)

    def _fade_out(self, duration: float) -> None:
        """Linearly fade brightness to 0, clear, then restore brightness.
        Blocking — always runs on a worker thread via _teardown_blocking."""
        steps = max(int(duration * self.FADE_FPS), 1)
        start_brightness = self._led.brightness
        if start_brightness <= 0:
            self._led.clear()
            return

        for i in range(1, steps + 1):
            self._led.set_brightness(start_brightness * (1.0 - i / steps))
            time.sleep(1.0 / self.FADE_FPS)

        self._led.clear()
        self._led.set_brightness(start_brightness)
