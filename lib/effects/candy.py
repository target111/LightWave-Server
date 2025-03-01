from lib.led import EffectBase

class CandyCane(EffectBase):
    """
    This effect creates a red-white candy cane
    """
    def _run(self, size=5, spacing=5):
        for j in range(255):  # Cycle through all colors (effectively shifting the pattern)
            for i in range(self.led.count):
                # Calculate which stripe the LED is part of
                stripe_index = (i + j) % (2 * (size + spacing))
                
                if stripe_index < size:
                    # Red stripe
                    self.led.set_pixel(i, (255, 0, 0))
                elif stripe_index >= size + spacing and stripe_index < 2 * size + spacing:
                    # White stripe
                    self.led.set_pixel(i, (255, 255, 255))
                else:
                    # Spacing between stripes, turn off
                    self.led.set_pixel(i, (0, 0, 0))

            self.led.show()
            if self.stopped.wait(0.07):
                return
