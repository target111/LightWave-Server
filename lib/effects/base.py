import abc
import datetime
import inspect
import logging
import threading
import time
from typing import Any, Callable, ClassVar

from lib.drivers.base import Color
from lib.drivers.controller import LEDController

__all__ = ["Color", "EffectBase", "option"]

logger = logging.getLogger(__name__)


def _coerce_color(value: Any) -> tuple[int, int, int]:
    r, g, b = value
    return (int(r), int(g), int(b))


def _coerce_bool(value: Any) -> bool:
    # JSON delivers real booleans, but values also arrive as numbers or
    # the string forms a form/query produces.
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


_COERCERS: dict[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "color": _coerce_color,
    "bool": _coerce_bool,
}


class Option:
    """One declared effect option. Created via `option()` in a class body
    and collected by `EffectBase.__init_subclass__`."""

    def __init__(
        self,
        default: Any,
        description: str,
        *,
        min: float | None = None,
        max: float | None = None,
    ):
        self.default = default
        self.description = description
        self.min = min
        self.max = max
        self.name = ""  # filled in from the attribute name
        self.type = ""  # filled in from the annotation

    def schema(self) -> dict:
        entry: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "description": self.description,
        }
        if self.min is not None:
            entry["min"] = self.min
        if self.max is not None:
            entry["max"] = self.max
        return entry


def option(
    default: Any,
    description: str,
    *,
    min: float | None = None,
    max: float | None = None,
) -> Any:
    """Declare an effect option in a class body:

        speed: float = option(1.0, "Speed multiplier", min=0.0)

    The option's type comes from the annotation (`int`, `float`, `bool`,
    or `Color`). Values passed to the effect are coerced to that type,
    checked against `min`/`max`, and set as an instance attribute, so the
    effect simply reads `self.speed`.

    Typed as `Any` (like `dataclasses.field`) so type checkers accept the
    assignment.
    """
    return Option(default, description, min=min, max=max)


def _option_type(cls_name: str, name: str, annotation: Any) -> str:
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is bool:
        return "bool"
    if annotation == Color or annotation == tuple[int, int, int]:
        return "color"
    raise TypeError(
        f"{cls_name}.{name}: unsupported option annotation {annotation!r}; "
        "use int, float, bool, or Color"
    )


class EffectBase(abc.ABC, threading.Thread):
    """Base class for animations.

    Writing an effect:
      - declare options with `option()` (see above)
      - initialize state in `setup()` (no `__init__` needed)
      - draw each frame in `tick(dt)` by writing RGB tuples into
        `self.pixels`; the loop pushes the buffer to the hardware after
        every tick. The buffer persists between frames — use
        `self.clear()` / `self.fill(color)` to reset it.
      - release sockets/files in `teardown()` (optional)

    Option conventions: times in seconds, sizes in pixels, rates per
    second, probabilities 0.0-1.0. Unitless tuning knobs are multipliers
    where 1.0 is the designed look; the tuned base value lives in the
    effect as a named constant."""

    # Generated from option() declarations; consumed by the registry/API.
    CONFIG_SCHEMA: ClassVar[list[dict]] = []
    _options: ClassVar[dict[str, Option]] = {}

    TARGET_FPS: int = 60

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "CONFIG_SCHEMA" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__}: CONFIG_SCHEMA is generated; declare "
                "options with option() instead"
            )

        options = dict(cls._options)
        annotations = inspect.get_annotations(cls)
        for name, value in list(cls.__dict__.items()):
            if not isinstance(value, Option):
                continue
            if name not in annotations:
                raise TypeError(
                    f"{cls.__name__}.{name}: option needs a type annotation"
                )
            value.name = name
            value.type = _option_type(cls.__name__, name, annotations[name])
            # Drop the marker so only the resolved instance attribute
            # remains; the annotation stays for type checkers.
            delattr(cls, name)
            if hasattr(cls, name):
                raise ValueError(
                    f"{cls.__name__}: option {name!r} clashes with an "
                    "existing attribute"
                )
            options[name] = value

        cls._options = options
        cls.CONFIG_SCHEMA = [opt.schema() for opt in options.values()]

    def __init__(self, led: LEDController, **kwargs):
        super().__init__(daemon=True, name=self.__class__.__name__)
        self.led = led
        self.n = led.count
        self.config = self._resolve_config(kwargs)
        for key, value in self.config.items():
            setattr(self, key, value)

        self.pixels: list[Color] = [(0, 0, 0)] * self.n
        self._stopped = threading.Event()
        self.start_time = datetime.datetime.now()
        self.setup()

    @classmethod
    def _resolve_config(cls, overrides: dict) -> dict:
        unknown = set(overrides) - set(cls._options)
        if unknown:
            logger.warning(
                "%s: ignoring unknown options %s",
                cls.__name__,
                sorted(unknown),
            )

        resolved = {}
        for name, opt in cls._options.items():
            value = overrides.get(name, opt.default)
            try:
                value = _COERCERS[opt.type](value)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"{cls.__name__}: bad value for option "
                    f"{name!r}: {value!r}"
                ) from e

            if opt.min is not None and value < opt.min:
                raise ValueError(
                    f"{cls.__name__}: option {name!r} must be "
                    f">= {opt.min}, got {value!r}"
                )
            if opt.max is not None and value > opt.max:
                raise ValueError(
                    f"{cls.__name__}: option {name!r} must be "
                    f"<= {opt.max}, got {value!r}"
                )

            resolved[name] = value

        return resolved

    def fill(self, color: Color) -> None:
        """Fill the frame buffer with one color (drawn on the next push)."""
        self.pixels = [color] * self.n

    def clear(self) -> None:
        """Reset the frame buffer to black."""
        self.fill((0, 0, 0))

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
                self.led.set_pixels(self.pixels)
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

    def setup(self) -> None:
        """Initialize effect state. Options are already resolved."""

    @abc.abstractmethod
    def tick(self, dt: float) -> None:
        """Advance the animation by `dt` seconds and draw one frame into
        `self.pixels`. Per-frame tuning constants assume TARGET_FPS, so
        effects scale them with `frames = dt * self.TARGET_FPS`."""

    def teardown(self) -> None: ...

    def stop(self) -> None:
        self._stopped.set()

    @property
    def is_stopped(self) -> bool:
        return self._stopped.is_set()
