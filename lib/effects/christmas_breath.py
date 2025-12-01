from lib.led import EffectBase
import math
import time

class ChristmasBreath(EffectBase):
    """
    Smoothly fades the entire strip between Red and Green.
    """
    def _run(self):
        period = 4.0  # Seconds for a full Red->Green->Red cycle
        
        start_time = time.time()
        
        while not self.stopped.is_set():
            # Calculate a value between 0.0 and 1.0 based on sine wave
            now = time.time()
            # (sin(t) + 1) / 2 shifts sine from [-1, 1] to [0, 1]
            phase = (math.sin((now - start_time) * 2 * math.pi / period) + 1) / 2
            
            # Interpolate Red and Green
            # Red: (255, 0, 0) -> Green: (0, 255, 0)
            r = int(255 * phase)
            g = int(255 * (1 - phase))
            b = 0
            
            # Use set_color (fill) for maximum performance
            self.led.set_color((r, g, b))
            
            # Short wait for smooth animation (approx 30-50 FPS)
            if self.stopped.wait(0.02):
                return
