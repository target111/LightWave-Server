from lib.led import EffectBase
import time

class CandyCane(EffectBase):
    """
    Rotating Red and White stripes resembling a candy cane.
    """
    def _run(self):
        # Configuration
        stripe_width = 5  # Number of pixels per color band
        speed = 0.05      # Lower is faster
        
        red = (255, 0, 0)
        white = (255, 255, 255)
        
        # Main loop
        offset = 0
        while not self.stopped.is_set():
            for i in range(self.led.count):
                # Determine color based on position and offset
                # We use modulo to create the repeating pattern
                if ((i + offset) // stripe_width) % 2 == 0:
                    self.led.set_pixel(i, red)
                else:
                    self.led.set_pixel(i, white)
            
            self.led.show()
            
            # Increment offset to make it move
            offset += 1
            
            # Reset offset to prevent overflow (optimization)
            if offset >= (stripe_width * 2):
                offset = 0
                
            if self.stopped.wait(speed):
                return
