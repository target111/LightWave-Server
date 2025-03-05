from lib.led import EffectBase

class RainbowCycle(EffectBase):
    """
    Draw rainbow that uniformly distributes itself across all pixels on the strip.
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

    def _run(self):
        for j in range(256):
            for i in range(self.led.count):
                pixel_index = (i * 256 // self.led.count) + j
                self.led.set_pixel(i, self.wheel(pixel_index & 255))
            self.led.show()
            if self.stopped.wait(0.1):
                return