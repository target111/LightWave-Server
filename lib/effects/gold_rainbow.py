import random
import datetime
from lib.led import EffectBase

class RainbowSparkle(EffectBase):
    """
    Displays a static rainbow with random gold sparkles.
    """

    def wheel(self, pos):
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)

    def _run(self):
        num_pixels = self.led.count

        # Create the rainbow base
        rainbow_colors = []
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels)
            color = self.wheel(pixel_index & 255)
            rainbow_colors.append(color)
            self.led.set_pixel(i, color)
        self.led.show()

        sparkle_duration = 0.5  # Seconds for a sparkle to stay on
        sparkle_interval = 0.1  # Seconds between new sparkles

        sparkles = {}  # Dictionary to track sparkles: {pixel_index: end_time}

        while not self.stopped.wait(sparkle_interval):
            # Remove expired sparkles
            now = datetime.datetime.now().timestamp()
            expired_sparkles = [i for i, end_time in sparkles.items() if end_time <= now]
            for i in expired_sparkles:
                self.led.set_pixel(i, rainbow_colors[i])  # Restore rainbow color
                del sparkles[i]

            # Add a new sparkle
            i = random.randint(0, num_pixels - 1)
            sparkles[i] = now + sparkle_duration
            self.led.set_pixel(i, (255, 255, 0))  # Gold sparkle

            self.led.show()
