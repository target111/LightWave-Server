from lib.led import EffectBase
import random

class SnowSparkle(EffectBase):
    """
    background with random white sparkles popping in and out.
    """
    def _run(self):
        # Configuration
        bg_color = (64, 160, 43) # Dim Green background
        sparkle_color = (255, 255, 255) # White
        sparkle_delay = 0.05 # How long the sparkle stays lit
        frequency_delay = 0.05 # Delay between sparkles
        
        # Set background once
        self.led.set_color(bg_color)
        
        while not self.stopped.is_set():
            # Pick a random pixel
            pixel = random.randint(0, self.led.count - 1)
            
            # Set to white
            self.led.set_pixel(pixel, sparkle_color)
            self.led.show()
            
            # Wait briefly (sparkle duration)
            if self.stopped.wait(sparkle_delay):
                return
            
            # Set back to background
            self.led.set_pixel(pixel, bg_color)
            self.led.show()
            
            # Randomize the delay slightly for a more natural look
            if self.stopped.wait(random.uniform(0.02, frequency_delay * 2)):
                return
