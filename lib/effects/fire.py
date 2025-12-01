from lib.led import EffectBase
import random

class Fire(EffectBase):
    """
    Simulates fire rising up the LED strip.
    """
    def _run(self):
        # Configuration
        cooling = 55
        sparking = 120
        speed_delay = 0.03
        
        # Initialize the heat cells
        heat = [0] * self.led.count
        
        # Pre-compute a 256-color palette (Black -> Red -> Yellow -> White)
        # This saves massive CPU during the animation loop
        palette = []
        for i in range(256):
            # Heat 0-85: Black to Red
            if i < 85:
                palette.append((i * 3, 0, 0))
            # Heat 85-170: Red to Yellow
            elif i < 170:
                palette.append((255, (i - 85) * 3, 0))
            # Heat 170-255: Yellow to White
            else:
                palette.append((255, 255, (i - 170) * 3))

        while not self.stopped.is_set():
            # Step 1: Cool down every cell a little
            for i in range(self.led.count):
                cooldown = random.randint(0, ((cooling * 10) // self.led.count) + 2)
                heat[i] = max(0, heat[i] - cooldown)
            
            # Step 2: Heat drifts "up" and diffuses
            # We iterate backwards
            for i in range(self.led.count - 1, 1, -1):
                heat[i] = (heat[i - 1] + heat[i - 2] + heat[i - 2]) // 3
            
            # Step 3: Randomly ignite new sparks at the bottom
            if random.randint(0, 255) < sparking:
                y = random.randint(0, 7) # Spark within first 7 pixels
                # Add heat, capped at 255
                heat[y] = min(255, heat[y] + random.randint(160, 255))
            
            # Step 4: Map heat to color palette
            for i in range(self.led.count):
                color_index = heat[i]
                # Ensure we don't go out of bounds
                if color_index >= 256: color_index = 255
                self.led.set_pixel(i, palette[color_index])
                
            self.led.show()
            
            if self.stopped.wait(speed_delay):
                return
