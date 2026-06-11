import abc
import datetime
import logging
import threading
import time
from typing import Any, Callable

from lib.drivers.controller import LEDController

logger = logging.getLogger(__name__)


def _coerce_color(value: Any) -> tuple[int, int, int]:
    r, g, b = value
    return (int(r), int(g), int(b))


_COERCERS: dict[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "color": _coerce_color,
}


def fade_factor(dt: float, fade_time: float, residual: float = 0.05) -> float:
    """Per-tick multiplier so an exponentially decaying value reaches
    `residual` of its starting point after `fade_time` seconds."""
    if fade_time <= 0:
        return 0.0
    return residual ** (dt / fade_time)


def scale_color(
    color: tuple[int, int, int], factor: float
) -> tuple[int, int, int]:
    """Scale an RGB tuple by a 0.0-1.0 brightness factor."""
    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
    )


def to_rgb255(r: float, g: float, b: float) -> tuple[int, int, int]:
    """Convert 0.0-1.0 float channels to a clamped 0-255 int tuple."""
    return (
        max(0, min(255, int(r * 255))),
        max(0, min(255, int(g * 255))),
        max(0, min(255, int(b * 255))),
    )


class EffectBase(abc.ABC, threading.Thread):
    """Base class for animations. Override `tick()` (mandatory) and
    `teardown()` (optional, for releasing sockets/files).

    Options declared in CONFIG_SCHEMA are resolved against the kwargs
    (defaults applied, values coerced to the declared type) and set as
    attributes, so an effect with `{"name": "speed", ...}` in its schema
    can simply read `self.speed`.

    Option conventions: times in seconds, sizes in pixels, rates per
    second, probabilities 0.0-1.0. Unitless tuning knobs are multipliers
    where 1.0 is the designed look; the tuned base value lives in the
    effect as a named constant."""

    CONFIG_SCHEMA: list[dict] = []
    TARGET_FPS: int = 60

    def __init__(self, led: LEDController, **kwargs):
        super().__init__(daemon=True, name=self.__class__.__name__)
        self.led = led
        self.config = self._resolve_config(kwargs)
        for key, value in self.config.items():
            setattr(self, key, value)

        self._stopped = threading.Event()
        self.start_time = datetime.datetime.now()

    @classmethod
    def _resolve_config(cls, overrides: dict) -> dict:
        known = {spec["name"] for spec in cls.CONFIG_SCHEMA}
        unknown = set(overrides) - known
        if unknown:
            logger.warning(
                "%s: ignoring unknown options %s",
                cls.__name__,
                sorted(unknown),
            )

        resolved = {}
        for spec in cls.CONFIG_SCHEMA:
            name = spec["name"]
            if hasattr(cls, name):
                raise ValueError(
                    f"{cls.__name__}: option {name!r} clashes with an "
                    "existing attribute"
                )
            value = overrides.get(name, spec["default"])
            coerce = _COERCERS.get(spec["type"])

            if coerce is not None:
                try:
                    value = coerce(value)
                except (TypeError, ValueError) as e:
                    raise ValueError(
                        f"{cls.__name__}: bad value for option "
                        f"{name!r}: {value!r}"
                    ) from e

            resolved[name] = value

        return resolved

    def run(self) -> None:
        frame_time = 1.0 / self.TARGET_FPS
        last = time.perf_counter()
        try:
            while not self._stopped.is_set():
                loop_start = time.perf_counter()
                # Clamp dt so a stall (GC pause, loaded CPU) doesn't
                # fast-forward the animation.
                dt = min(loop_start - last, 3 * frame_time)
                last = loop_start
                self.tick(dt)
                self.led.show()
                wait = frame_time - (time.perf_counter() - loop_start)
                if wait > 0 and self._stopped.wait(wait):
                    break
        except Exception:
            logger.exception("Effect %s crashed", self.name)
        finally:
            try:
                self.teardown()
            except Exception:
                logger.exception("Teardown of %s failed", self.name)

    @abc.abstractmethod
    def tick(self, dt: float) -> None:
        """Advance the animation by `dt` seconds and draw one frame.
        Per-frame tuning constants assume TARGET_FPS, so effects scale
        them with `frames = dt * self.TARGET_FPS`."""

    def teardown(self) -> None: ...

    def stop(self) -> None:
        self._stopped.set()

    @property
    def is_stopped(self) -> bool:
        return self._stopped.is_set()
