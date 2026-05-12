import importlib
import inspect
import logging
import pkgutil
from typing import Type

from lib.effects.base import EffectBase

logger = logging.getLogger(__name__)

_SKIP_MODULES = {"base", "registry"}


class EffectRegistry:
    def __init__(self):
        self._effects: dict[str, Type[EffectBase]] = {}
        self._load_all()

    def _load_all(self) -> None:
        from lib import effects as effects_pkg

        for _, name, _ in pkgutil.iter_modules(effects_pkg.__path__):
            if name.startswith("_") or name in _SKIP_MODULES:
                continue

            try:
                module = importlib.import_module(
                    f"{effects_pkg.__name__}.{name}"
                )
            except Exception:
                logger.exception("Failed to load effect module %s", name)
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, EffectBase)
                    and obj is not EffectBase
                    and obj.__module__ == module.__name__
                ):
                    self._effects[obj.__name__] = obj
                    logger.info("Registered effect: %s", obj.__name__)

    def get(self, name: str) -> Type[EffectBase]:
        if name not in self._effects:
            raise KeyError(name)
        return self._effects[name]

    def has(self, name: str) -> bool:
        return name in self._effects

    def names(self) -> list[str]:
        return sorted(self._effects.keys())

    def describe(self, name: str) -> str:
        return (self.get(name).__doc__ or "").strip()

    def schema(self, name: str) -> list[dict]:
        return self.get(name).CONFIG_SCHEMA
