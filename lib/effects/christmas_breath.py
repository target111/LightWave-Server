from lib.led import EffectBase
import math
import time

class ChristmasBreath(EffectBase):
    """
    Smoothly fades the entire strip between Red and Green.
    """
    def tick(self):
        period = 4.0
        now = time.time()
        # self.start_time is from EffectBase
        # We use elapsed time
        
        phase = (math.sin((now - self.start_time.timestamp()) * 2 * math.pi / period) + 1) / 2
        
        r = int(255 * phase)
        g = int(255 * (1 - phase))
        b = 0
        
        self.led.set_color((r, g, b))