import random
import datetime
import time
from lib.led import EffectBase

class RainbowSparklePulse(EffectBase):
    """
    Displays a static rainbow with random gold sparkles that radiate outwards.
    """

    def wheel(self, pos):
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)

    def create_rainbow_base(self, num_pixels):
        """Create the initial rainbow pattern."""
        rainbow_colors = []
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels)
            color = self.wheel(pixel_index & 255)
            rainbow_colors.append(color)
            self.led.set_pixel(i, color)
        self.led.show()
        return rainbow_colors

    def generate_sparkle_color(self):
        """Generate a random color for the sparkle and its radiate effect."""
        colors = [(255, 255, 0), (255, 0, 0), (255, 165, 0)]  # Gold, Red, Orange
        return random.choice(colors)

    def radiate_sparkle(self, center_index, sparkle_color, rainbow_colors):
        """Create a radiate effect around the sparkle."""
        radius = random.randint(1, 3)  # Radiate up to 3 pixels away
        for i in range(center_index - radius, center_index + radius + 1):
            if 0 <= i < self.led.count:
                if i != center_index:
                    fade_factor = 1 - abs(center_index - i) / (radius + 1) # further the sparkle goes from the center, the more it fades
                    faded_color = tuple(int(c * fade_factor) for c in sparkle_color)
                    # Blend with the rainbow color underneath
                    blended_color = tuple(int((rc + fc) / 2) for rc, fc in zip(rainbow_colors[i], faded_color))
                    self.led.set_pixel(i, blended_color)

    def _run(self):
        num_pixels = self.led.count
        rainbow_colors = self.create_rainbow_base(num_pixels)

        sparkle_duration = 0.7  # Seconds for a sparkle to stay on
        radiate_duration = 0.5 # Seconds for the radiate effect to stay on
        sparkle_interval = 0.2  # Seconds between new sparkles

        sparkles = {}  # Dictionary to track sparkles: {pixel_index: (end_time, radiate_end_time, sparkle_color)}

        while not self.stopped.wait(sparkle_interval):
            now = time.time()

            # Remove expired sparkles and radiate effects
            expired_sparkles = []
            for i, (end_time, radiate_end_time, _) in sparkles.items():
                if end_time <= now:
                    self.led.set_pixel(i, rainbow_colors[i])  # Restore rainbow color
                    expired_sparkles.append(i)
                elif radiate_end_time <= now:
                    self.radiate_sparkle(i, rainbow_colors[i], rainbow_colors) # Restore radiate pixels to rainbow

            for i in expired_sparkles:
                del sparkles[i]

            # Add a new sparkle with radiate effect
            i = random.randint(0, num_pixels - 1)
            sparkle_color = self.generate_sparkle_color()
            sparkles[i] = (now + sparkle_duration, now + radiate_duration, sparkle_color)
            self.led.set_pixel(i, sparkle_color)
            self.radiate_sparkle(i, sparkle_color, rainbow_colors)

            self.led.show()
