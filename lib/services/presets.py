import contextlib
import json
import logging
import os
import re
import tempfile
import threading
from pathlib import Path

from lib.effects.registry import EffectRegistry

logger = logging.getLogger(__name__)

# Preset names must be usable as URL path segments and CLI arguments.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class PresetError(ValueError):
    """Invalid preset submitted by a client (bad name, unknown effect,
    bad args). The message is safe to return as the API error detail."""


class PresetNotFoundError(KeyError):
    pass


class PresetStore:
    """User presets: an effect name plus saved option values, shared by
    every client. Backed by one human-editable JSON file (a name-keyed
    object) written atomically. All access goes through one lock because
    API handlers run on a threadpool."""

    def __init__(self, path: Path, registry: EffectRegistry):
        self._path = path
        self._registry = registry
        self._lock = threading.Lock()
        self._presets: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        try:
            raw = json.loads(self._path.read_text())
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to load presets from %s", self._path)
            return {}

        if not isinstance(raw, dict):
            logger.error("Presets file %s is not a JSON object", self._path)
            return {}

        # Tolerate hand-edited entries: keep anything shaped right and
        # drop the rest loudly. Args are only validated against the
        # effect schema on save/start — the effect may not even be
        # installed right now.
        presets = {}
        for name, body in raw.items():
            if isinstance(body, dict) and isinstance(body.get("effect"), str):
                presets[name] = {
                    "effect": body["effect"],
                    "args": body.get("args") or {},
                    "description": str(body.get("description") or ""),
                }
            else:
                logger.error("Skipping malformed preset %r", name)
        return presets

    def _write_locked(self) -> None:
        """Atomic replace so a crash mid-write can't corrupt the file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=self._path.parent, prefix=self._path.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._presets, f, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp, self._path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise

    @staticmethod
    def _record(name: str, body: dict) -> dict:
        """A stored body plus its name — the shape clients see."""
        return {"name": name, **body}

    def list(self) -> list[dict]:
        with self._lock:
            return [
                self._record(name, body)
                for name, body in sorted(self._presets.items())
            ]

    def get(self, name: str) -> dict:
        with self._lock:
            if name not in self._presets:
                raise PresetNotFoundError(name)
            return self._record(name, self._presets[name])

    def save(
        self, name: str, effect: str, args: dict, description: str
    ) -> dict:
        """Create or replace a preset. Args are validated against the
        effect's schema and stored in coerced (canonical) form."""
        if not _NAME_RE.match(name):
            raise PresetError(
                "Preset names must be 1-64 characters: letters, digits, "
                "'-' or '_', starting with a letter or digit"
            )
        if self._registry.has(name):
            raise PresetError(
                f"{name!r} is an effect name; preset names must not "
                "shadow effects"
            )
        if not self._registry.has(effect):
            raise PresetError(f"Unknown effect {effect!r}")

        try:
            args = self._registry.get(effect).validate_options(args)
        except ValueError as e:
            raise PresetError(str(e)) from e

        body = {"effect": effect, "args": args, "description": description}
        with self._lock:
            self._presets[name] = body
            self._write_locked()
        return self._record(name, body)

    def delete(self, name: str) -> None:
        with self._lock:
            if name not in self._presets:
                raise PresetNotFoundError(name)
            del self._presets[name]
            self._write_locked()
