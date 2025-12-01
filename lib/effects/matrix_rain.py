from lib.led import EffectBase
import random

class MatrixRain(EffectBase):
    """
    Green 'code' drops that are guaranteed to reach the bottom of the strip.
    """
    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        # Adjust spawn rate for 60 FPS (was 50 FPS)
        self.spawn_rate = 0.05 * (50/60)
        self.min_speed = 0.2 * (50/60) # Scale speed per frame
        self.max_speed = 0.8 * (50/60)
        self.trail_length = 20
        
        self.head_color = (180, 255, 180)
        self.tail_color = (0, 255, 0)
        
        self.drops = []

    def tick(self):
        # Spawn
        if random.random() < self.spawn_rate:
            self.drops.append([0.0, random.uniform(self.min_speed, self.max_speed)])
        
        pixel_buffer = {}
        active_drops = []
        
        for drop in self.drops:
            pos, speed = drop
            pos += speed
            
            head_pixel = int(pos)
            
            if head_pixel - self.trail_length < self.led.count:
                active_drops.append([pos, speed])
                
                for i in range(self.trail_length):
                    pixel_index = head_pixel - i
                    if 0 <= pixel_index < self.led.count:
                        intensity = 1.0 - (i / self.trail_length)
                        current_val = pixel_buffer.get(pixel_index, 0.0)
                        pixel_buffer[pixel_index] = max(current_val, intensity)
        
        self.drops = active_drops

        for i in range(self.led.count):
            if i in pixel_buffer:
                intensity = pixel_buffer[i]
                if intensity > 0.9:
                    r = int(self.head_color[0] * intensity)
                    g = int(self.head_color[1] * intensity)
                    b = int(self.head_color[2] * intensity)
                else:
                    r = int(self.tail_color[0] * intensity)
                    g = int(self.tail_color[1] * intensity)
                    b = int(self.tail_color[2] * intensity)
                self.led.set_pixel(i, (r, g, b))
            else:
                self.led.set_pixel(i, (0, 0, 0))