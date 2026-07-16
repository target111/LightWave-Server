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
    # Membership against `choices` is checked in _resolve_config, which
    # has the option in hand; here we only normalize to a string.
    "enum": str,
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
        choices: list[str] | None = None,
    ):
        self.default = default
        self.description = description
        self.min = min
        self.max = max
        self.choices = choices
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
        if self.choices is not None:
            entry["choices"] = self.choices
        return entry


def option(
    default: Any,
    description: str,
    *,
    min: float | None = None,
    max: float | None = None,
    choices: list[str] | None = None,
) -> Any:
    """Declare an effect option in a class body:

        speed: float = option(1.0, "Speed multiplier", min=0.0)
        mode: str = option("warm", "Palette", choices=["warm", "cool"])

    The option's type comes from the annotation (`int`, `float`, `bool`,
    `Color`, or `str`). Values passed to the effect are coerced to that
    type, checked against `min`/`max` (numbers) or `choices` (`str`), and
    set as an instance attribute, so the effect simply reads `self.speed`.

    A `str` option must supply a non-empty `choices` list — the value is
    validated against it and the API renders a dropdown — so options stay
    a closed, self-describing set rather than free text.

    Typed as `Any` (like `dataclasses.field`) so type checkers accept the
    assignment.
    """
    return Option(default, description, min=min, max=max, choices=choices)


def _option_type(cls_name: str, name: str, annotation: Any) -> str:
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is bool:
        return "bool"
    if annotation is str:
        return "enum"
    # Color is tuple[int, int, int]; a literal tuple annotation compares
    # equal, so this covers both spellings.
    if annotation == Color:
        return "color"
    raise TypeError(
        f"{cls_name}.{name}: unsupported option annotation {annotation!r}; "
        "use int, float, bool, str, or Color"
    )


def _check_choices(cls_name: str, opt: "Option") -> None:
    """Enforce that `choices` and a `str`/enum option go together: a str
    option needs a non-empty list of string choices whose members include
    the default, and `choices` is meaningless on any other type."""
    if opt.type == "enum":
        if not opt.choices:
            raise TypeError(
                f"{cls_name}.{opt.name}: a str option needs a non-empty "
                "choices= list"
            )
        if any(not isinstance(c, str) for c in opt.choices):
            raise TypeError(
                f"{cls_name}.{opt.name}: choices must all be strings"
            )
        if opt.default not in opt.choices:
            raise ValueError(
                f"{cls_name}.{opt.name}: default {opt.default!r} is not "
                f"one of choices {opt.choices}"
            )
    elif opt.choices is not None:
        raise TypeError(
            f"{cls_name}.{opt.name}: choices= only applies to str options"
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

    # Public effect name: the key clients start it by and the string
    # stored in presets. Defaults to the class name, so setting it is only
    # needed to keep the published name stable across a class rename.
    NAME: ClassVar[str]

    # Generated from option() declarations; consumed by the registry/API.
    CONFIG_SCHEMA: ClassVar[list[dict]] = []
    _options: ClassVar[dict[str, Option]] = {}

    TARGET_FPS: int = 60

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Checked against __dict__ so a subclass never inherits a parent's
        # explicit NAME: each class defaults to its own name.
        if "NAME" not in cls.__dict__:
            cls.NAME = cls.__name__
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
            _check_choices(cls.__name__, value)
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
        super().__init__(daemon=True, name=self.NAME)
        self.led = led
        self.n = led.count
        self.config = self._resolve_config(kwargs)
        for key, value in self.config.items():
            setattr(self, key, value)

        self.pixels: list[Color] = [(0, 0, 0)] * self.n
        self._stopped = threading.Event()
        self._finished = False
        # Fired from this thread when run() exits for any reason
        # (stopped, finished, crashed). Must be cheap and thread-safe.
        self.on_finished: Callable[[], None] | None = None
        self.start_time = datetime.datetime.now(datetime.UTC)
        self.setup()

    @classmethod
    def validate_options(cls, overrides: dict) -> dict:
        """Strictly check a partial set of option values — unknown names
        are an error, unlike construction which just warns — and return
        only those values, coerced to their declared types. Used to vet
        preset args before they are persisted."""
        resolved = cls._resolve_config(overrides, strict=True)
        return {name: resolved[name] for name in overrides}

    @classmethod
    def _resolve_config(cls, overrides: dict, *, strict: bool = False) -> dict:
        unknown = set(overrides) - set(cls._options)
        if unknown:
            if strict:
                raise ValueError(
                    f"{cls.NAME}: unknown options {sorted(unknown)}"
                )
            logger.warning(
                "%s: ignoring unknown options %s",
                cls.NAME,
                sorted(unknown),
            )

        resolved = {}
        for name, opt in cls._options.items():
            value = overrides.get(name, opt.default)
            try:
                value = _COERCERS[opt.type](value)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"{cls.NAME}: bad value for option "
                    f"{name!r}: {value!r}"
                ) from e

            if opt.min is not None and value < opt.min:
                raise ValueError(
                    f"{cls.NAME}: option {name!r} must be "
                    f">= {opt.min}, got {value!r}"
                )
            if opt.max is not None and value > opt.max:
                raise ValueError(
                    f"{cls.NAME}: option {name!r} must be "
                    f"<= {opt.max}, got {value!r}"
                )
            if opt.choices is not None and value not in opt.choices:
                raise ValueError(
                    f"{cls.NAME}: option {name!r} must be one of "
                    f"{opt.choices}, got {value!r}"
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
            # Set before firing the callback: is_alive() stays true until
            # the thread fully exits, so observers woken by on_finished
            # need `finished` to already reflect this exit.
            self._finished = True
            if self.on_finished is not None:
                self.on_finished()

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
    def finished(self) -> bool:
        """True once run() has exited (stopped, finished, or crashed)."""
        return self._finished
