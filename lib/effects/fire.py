from lib.led import EffectBase
import random

class FireFlicker(EffectBase):
    """
    This effect simulates the flickering of a fire.
    """
    def _run(self, intensity=0.7, speed=0.2):
        for i in range(self.led.count):
            flicker = random.randint(0, int(255 * intensity))
            self.led.set_pixel(i, (min(255, flicker + 100), flicker, 0))

        self.led.show()
        if self.stopped.wait(speed):
            return
