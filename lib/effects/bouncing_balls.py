from lib.led import EffectBase
import time

class BouncingBalls(EffectBase):
    """
    Simulates multi-colored balls bouncing under gravity.
    """
    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        # Physics Constants
        self.gravity = -5.81
        self.start_height = 1
        self.dampening = 0.90
        
        self.num_balls = 3
        self.colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        
        self.start_times = [0.0] * self.num_balls
        self.velocities = [0.0] * self.num_balls
        self.heights = [self.start_height] * self.num_balls
        
        now = time.time()
        for i in range(self.num_balls):
            self.start_times[i] = now + (i * 0.5)
            self.velocities[i] = 0.0

    def tick(self):
        now = time.time()
        self.led.clear()
        
        for i in range(self.num_balls):
            t = now - self.start_times[i]
            if t < 0: continue

            h = 0.5 * self.gravity * pow(t, 2) + self.velocities[i] * t + self.heights[i]
            
            if h < 0:
                h = 0
                v_impact = self.velocities[i] + self.gravity * t
                new_v = -v_impact * self.dampening
                
                self.start_times[i] = now
                self.heights[i] = 0
                self.velocities[i] = new_v
                
                if new_v < 1.0: 
                    self.heights[i] = self.start_height
                    self.velocities[i] = 0
                    self.start_times[i] = now + 1.0

            position = int(h * (self.led.count - 1))
            
            if 0 <= position < self.led.count:
                self.led.set_pixel(position, self.colors[i % len(self.colors)])