import random
import datetime
from lib.led import EffectBase

class GlitchyRainbowFireworks(EffectBase):
    """
    Displays a rainbow with glitchy, firework-like sparkles.
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

        sparkle_duration = 0.5  # Seconds for a sparkle to last
        sparkle_interval = 0.05 # Seconds between new sparkles (faster for more fireworks)
        glitch_radius    = 4    # Number of pixels affected around the sparkle
        glitch_intensity = 0.5  # Probability of a pixel glitching

        sparkles = {} # Dictionary to track sparkles: {pixel_index: (end_time, color)}

        while not self.stopped.wait(sparkle_interval):
            # Remove expired sparkles and their effects
            now = datetime.datetime.now().timestamp()
            expired_sparkles = [i for i, (end_time, _) in sparkles.items() if end_time <= now]
            for i in expired_sparkles:
                self.led.set_pixel(i, rainbow_colors[i])  # Restore original color

                # Remove glitch effects from neighbors
                for j in range(max(0, i - glitch_radius), min(num_pixels, i + glitch_radius + 1)):
                    if j not in sparkles:  # Only restore if not currently a sparkle itself
                        self.led.set_pixel(j, rainbow_colors[j])
                del sparkles[i]

            # Add a new sparkle with random firework color
            i = random.randint(0, num_pixels - 1)
            sparkle_color = random.choice([
                (255, 255, 0),   # Gold
                (255, 0, 0),     # Red
                (0, 255, 0),     # Green
                (0, 0, 255),     # Blue
                (255, 105, 180), # Hot Pink
                (128, 0, 128),   # Purple
                (255, 255, 255)  # White (for bright bursts)
            ])
            sparkles[i] = (now + sparkle_duration, sparkle_color)
            self.led.set_pixel(i, sparkle_color)

            # Apply glitch effect to nearby pixels
            for j in range(max(0, i - glitch_radius), min(num_pixels, i + glitch_radius + 1)):
                if random.random() < glitch_intensity:
                    if random.random() < 0.5:
                        # Option 1: Briefly set to the sparkle color for a "spreading" effect
                        self.led.set_pixel(j, sparkle_color)
                    else:
                        # Option 2: Randomly glitch the color
                        glitch_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                        self.led.set_pixel(j, glitch_color)

            self.led.show()
