import abc

import neopixel
import threading
import pkgutil
import inspect
import datetime


class EffectBase(abc.ABC, threading.Thread):
    def __init__(self, led):
        super().__init__()
        self.led = led

        # Event to stop the threads
        self.stopped = threading.Event()

        # Store start time to keep track of how long the effect has been running
        self.start_time = datetime.datetime.now()

    def run(self):
        while not self.stopped.wait(0.1):
            self._run()

    @abc.abstractmethod
    def _run(self):
        pass

    def stop(self):
        self.stopped.set()
        self.led.clear()


class EffectRegistry(object):
    def __init__(self):
        self.effects = {}

        # Look for effects in the effects folder and register them if they are valid
        self._load_effects()

    def _register(self, effect: object):
        if issubclass(effect, EffectBase) and effect != EffectBase:
            self.effects[effect.__name__] = effect

    def _load_effects(self):
        for _, name, _ in pkgutil.iter_modules(["lib/effects"]):
            self.import_effect(name)

    def import_effect(self, name: str):
        effect = pkgutil.find_loader(f"{__package__}.effects.{name}")

        if not effect:
            raise ImportError(f"Effect {name} not found")

        for _, obj in inspect.getmembers(effect.load_module(), inspect.isclass):
            self._register(obj)

    def get(self, name: str):
        if not self.is_effect(name):
            raise KeyError(f"Effect {name} not found")

        return self.effects[name]

    def get_all(self):
        return self.effects

    def get_names(self):
        return self.effects.keys()

    def get_description(self, name: str):
        if not self.is_effect(name):
            raise KeyError(f"Effect {name} not found")

        return self.effects[name].__doc__
    
    def is_effect(self, name: str):
        if name not in self.effects:
            return False
        
        return True


class LED(object):
    def __init__(self, pin, num_pixels: int, auto_write: bool = False):
        self.auto_write = auto_write

        self.led = neopixel.NeoPixel(pin, num_pixels, auto_write=self.auto_write)
        # self.led = MockLed(num_pixels)

    @property
    def count(self):
        return self.led.n

    def set_color(self, color: tuple):
        self.led.fill(color)

        if not self.auto_write:
            self.show()
    
    def set_brightness(self, brightness: float):
        self.led.brightness = brightness

        if not self.auto_write:
            self.show()

    def set_pixel(self, pixel: int, color: tuple):
        self.led[pixel] = color

    def show(self):
        self.led.show()

    def clear(self):
        self.set_color((0, 0, 0))


class MockLed(object):
    def __init__(self, num_pixels: int):
        self.pixels = [0] * num_pixels
        self.brightness = 1.0
        self.n = len(self.pixels)

    def __getitem__(self, key):
        return self.pixels[key]

    def fill(self, color: tuple):
        print(f"fill: {color}")

    def show(self):
        print("show")

    def set_color(self, color: tuple):
        print(f"set_color: {color}")
