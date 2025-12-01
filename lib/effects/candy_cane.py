from lib.led import EffectBase

class CandyCane(EffectBase):
    """
    Rotating Red and White stripes resembling a candy cane.
    """
    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.offset = 0.0
        self.stripe_width = 5
        # Original speed 0.05 (20 FPS). Moves 1 pixel per frame. 20 px/sec.
        # New 60 FPS. Need 20 px/sec => 0.33 px/frame.
        self.speed = 0.33
        self.red = (255, 0, 0)
        self.white = (255, 255, 255)

    def tick(self):
        current_offset = int(self.offset)
        for i in range(self.led.count):
            if ((i + current_offset) // self.stripe_width) % 2 == 0:
                self.led.set_pixel(i, self.red)
            else:
                self.led.set_pixel(i, self.white)
        
        self.offset += self.speed
        if self.offset >= (self.stripe_width * 2):
            self.offset -= (self.stripe_width * 2)