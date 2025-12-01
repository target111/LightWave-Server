from lib.led import EffectBase
import random

class SnowSparkle(EffectBase):
    """
    background with random white sparkles popping in and out.
    """
    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.bg_color = (64, 160, 43)
        self.sparkle_color = (255, 255, 255)
        self.sparkle_delay = 0.05
        self.frequency_delay = 0.05
        
        self.state = 0 # 0 = Wait for sparkle, 1 = Sparkle active
        self.timer = 0.0
        self.next_event_time = 0.0
        self.active_pixel = -1
        
        self.led.set_color(self.bg_color)

    def tick(self):
        self.timer += (1.0 / 60.0) # Approx dt
        
        if self.state == 0: # Waiting to sparkle
            if self.timer >= self.next_event_time:
                # Trigger sparkle
                self.active_pixel = random.randint(0, self.led.count - 1)
                self.led.set_pixel(self.active_pixel, self.sparkle_color)
                
                self.state = 1
                self.timer = 0.0
                self.next_event_time = self.sparkle_delay
                
        elif self.state == 1: # Sparkle is on
            if self.timer >= self.next_event_time:
                # Turn off sparkle
                if self.active_pixel != -1:
                    self.led.set_pixel(self.active_pixel, self.bg_color)
                
                self.state = 0
                self.timer = 0.0
                self.next_event_time = random.uniform(0.02, self.frequency_delay * 2)