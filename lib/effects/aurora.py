from lib.led import EffectBase
import math
import time

class Aurora(EffectBase):
    """
    Smooth, flowing waves of Green, Blue and Purple (Northern Lights).
    """
    def _run(self):
        t = 0
        speed = 0.05
        
        while not self.stopped.is_set():
            # t moves forward to animate
            t += 0.1
            
            for i in range(self.led.count):
                # Create two sine waves with different frequencies
                # i * 0.1 scales the wave across the strip
                wave1 = math.sin(i * 0.1 + t)
                wave2 = math.sin(i * 0.05 - t * 0.5) # slower, wider, backwards
                
                # Combine waves to get a value roughly between -2 and 2
                combined = wave1 + wave2
                
                # Map the combined wave to RGB values
                # We want Green/Blue dominance for Aurora look
                
                # Red is low, only peaks slightly for purple
                r = int((math.sin(combined) + 1) * 30) 
                
                # Green follows the main wave
                g = int((math.sin(combined + 2) + 1) * 100) 
                
                # Blue is always present but shifts
                b = int((math.sin(combined + 4) + 1) * 100)
                
                # Clamp values to 0-255 just in case
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                
                self.led.set_pixel(i, (r, g, b))
                
            self.led.show()
            
            if self.stopped.wait(speed):
                return
