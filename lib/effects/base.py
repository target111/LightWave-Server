import abc
import datetime
import logging
import threading
import time

from lib.drivers.controller import LEDController

logger = logging.getLogger(__name__)


class EffectBase(abc.ABC, threading.Thread):
    """Base class for animations. Override `tick()` (mandatory) and
    `teardown()` (optional, for releasing sockets/files)."""

    CONFIG_SCHEMA: list[dict] = []
    TARGET_FPS: int = 60

    def __init__(self, led: LEDController, **kwargs):
        super().__init__(daemon=True, name=self.__class__.__name__)
        self.led = led
        self.config = kwargs
        self._stopped = threading.Event()
        self.start_time = datetime.datetime.now()

    def run(self) -> None:
        frame_time = 1.0 / self.TARGET_FPS
        try:
            while not self._stopped.is_set():
                loop_start = time.perf_counter()
                self.tick()
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
    def tick(self) -> None: ...

    def teardown(self) -> None: ...

    def stop(self) -> None:
        self._stopped.set()

    @property
    def is_stopped(self) -> bool:
        return self._stopped.is_set()
