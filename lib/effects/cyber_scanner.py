from lib.led import EffectBase
import time

class CyberScanner(EffectBase):
    """
    A moving 'eye' that leaves a fading trail behind it.
    """
    def _run(self):
        # Configuration
        eye_color = (255, 0, 255) # Magenta (Cyberpunk style)
        decay = 0.95              # How fast the trail fades (lower = shorter trail)
        speed = 0.03              # Speed of the eye
        
        # Internal buffer to store brightness of every pixel (0.0 to 1.0)
        # We use this to calculate physics without querying the hardware
        heat = [0.0] * self.led.count
        
        position = 0
        direction = 1
        
        while not self.stopped.is_set():
            # 1. Fade out everything slightly
            for i in range(self.led.count):
                heat[i] = heat[i] * decay
            
            # 2. Set the "Head" of the scanner to full brightness
            heat[position] = 1.0
            
            # 3. Render the output
            for i in range(self.led.count):
                # Calculate color brightness based on heat
                pixel_r = int(eye_color[0] * heat[i])
                pixel_g = int(eye_color[1] * heat[i])
                pixel_b = int(eye_color[2] * heat[i])
                
                self.led.set_pixel(i, (pixel_r, pixel_g, pixel_b))
            
            self.led.show()
            
            # 4. Move the eye
            position += direction
            
            # Bounce logic
            if position >= self.led.count - 1:
                position = self.led.count - 1
                direction = -1
            elif position <= 0:
                position = 0
                direction = 1
                
            if self.stopped.wait(speed):
                return
