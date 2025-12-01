from lib.led import EffectBase
import random

class StarryNightColor(EffectBase):
    """
    Randomly fades multi-colored stars in and out smoothly.
    """
    def _run(self):
        # Configuration
        density = 0.02 # Chance a dark pixel lights up
        fade_speed = 10 # Slower fade for a calmer look
        
        # Star Color Palette
        # We use a mix of realistic star colors (White, Blue-ish, Yellow-ish)
        # plus a few extras for variety.
        palette = [
            (255, 255, 255), # Pure White
            (200, 200, 255), # Blue-White (Rigel)
            (255, 240, 150), # Pale Yellow (Sun-like)
            (255, 200, 100), # Amber/Orange (Arcturus)
            (150, 150, 255), # Deep Blue
            (255, 180, 220), # Faint Red/Pink
        ]

        # State definitions
        STATE_OFF = 0
        STATE_IN = 1
        STATE_OUT = 2
        
        # Initialize arrays to track state for every pixel
        states = [STATE_OFF] * self.led.count
        brightness = [0] * self.led.count
        
        # We also need to track WHICH color a specific pixel is currently displaying
        pixel_colors = [(0,0,0)] * self.led.count

        while not self.stopped.is_set():
            for i in range(self.led.count):
                
                # State Machine
                if states[i] == STATE_OFF:
                    if random.random() < density:
                        states[i] = STATE_IN
                        # Pick a random color for this specific star instance
                        pixel_colors[i] = random.choice(palette)
                        
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
                    current_color = pixel_colors[i]
                    
                    # Apply brightness scaling
                    # We use integer math for speed where possible, 
                    # but float multiplication is usually clean enough here.
                    b_factor = brightness[i] / 255.0
                    
                    r = int(current_color[0] * b_factor)
                    g = int(current_color[1] * b_factor)
                    b = int(current_color[2] * b_factor)
                    
                    self.led.set_pixel(i, (r, g, b))
                else:
                    self.led.set_pixel(i, (0, 0, 0))

            self.led.show()
            
            if self.stopped.wait(0.05):
                return
