import importlib
import inspect
import logging
import pkgutil

from lib.effects.base import EffectBase

logger = logging.getLogger(__name__)


class EffectRegistry:
    def __init__(self):
        self._effects: dict[str, type[EffectBase]] = {}
        self._load_all()

    def _load_all(self) -> None:
        from lib.effects import library

        for _, name, _ in pkgutil.iter_modules(library.__path__):
            if name.startswith("_"):
                continue

            try:
                module = importlib.import_module(f"{library.__name__}.{name}")
            except Exception:
                logger.exception("Failed to load effect module %s", name)
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, EffectBase)
                    and obj is not EffectBase
                    and obj.__module__ == module.__name__
                ):
                    if obj.NAME in self._effects:
                        logger.error(
                            "Effect name %r from %s already registered by "
                            "%s; skipping",
                            obj.NAME,
                            obj.__qualname__,
                            self._effects[obj.NAME].__qualname__,
                        )
                        continue
                    self._effects[obj.NAME] = obj
                    logger.info("Registered effect: %s", obj.NAME)

    def get(self, name: str) -> type[EffectBase]:
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
