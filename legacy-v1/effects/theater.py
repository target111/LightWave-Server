import random
from lib.led import EffectBase

class TheaterChase(EffectBase):
    """
    This effect creates a chasing light pattern, reminiscent of old theater marquee lights.
    """
    def wheel(self, pos):
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)

    def chase(self, color, wait=0.05, iterations=10):
        for _ in range(iterations):
            for q in range(3):
                for i in range(0, self.led.count, 3):
                    self.led.set_pixel(i + q, color)

                    self.led.show()
                    self.stopped.wait(wait)

                for i in range(0, self.led.count, 3):
                    self.led.set_pixel(i + q, (0, 0, 0))

    def _run(self):
        #chase((255, 0, 0))
        #chase((0, 255, 0))
        #chase((0, 0, 255))
        self.chase(self.wheel(random.randint(0, 255)))
