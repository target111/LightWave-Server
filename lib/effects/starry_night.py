from lib.led import EffectBase
import random

class StarryNight(EffectBase):
    """
    Randomly fades stars in and out smoothly.
    """
    def _run(self):
        # Configuration
        density = 0.02 # Chance a dark pixel lights up
        fade_speed = 15 # How fast brightness changes per frame (0-255)
        
        # State definitions
        STATE_OFF = 0
        STATE_IN = 1
        STATE_OUT = 2
        
        # Initialize arrays
        states = [STATE_OFF] * self.led.count
        brightness = [0] * self.led.count
        
        color = (255, 255, 255) # White stars

        while not self.stopped.is_set():
            for i in range(self.led.count):
                
                # State Machine
                if states[i] == STATE_OFF:
                    if random.random() < density:
                        states[i] = STATE_IN
                        
                elif states[i] == STATE_IN:
                    brightness[i] += fade_speed
                    if brightness[i] >= 255:
                        brightness[i] = 255
                        states[i] = STATE_OUT
                        
                elif states[i] == STATE_OUT:
                    brightness[i] -= fade_speed
                    if brightness[i] <= 0:
                        brightness[i] = 0
                        states[i] = STATE_OFF
                
                # Apply Color
                # Optimization: Only write to LED if it's lit
                if brightness[i] > 0:
                    # Apply brightness to the color
                    b_factor = brightness[i] / 255.0
                    r = int(color[0] * b_factor)
                    g = int(color[1] * b_factor)
                    b = int(color[2] * b_factor)
                    self.led.set_pixel(i, (r, g, b))
                else:
                    self.led.set_pixel(i, (0, 0, 0))

            self.led.show()
            
            if self.stopped.wait(0.05):
                return
