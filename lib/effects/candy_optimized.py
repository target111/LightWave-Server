from lib.led import EffectBase

class CandyCaneOptimized(EffectBase):
    """
    Optimized candy cane effect for the given LED class.
    """
    def _run(self, size=7, spacing=2):
        offset = 0
        stripe_cycle = 2 * (size + spacing)

        while not self.stopped.wait(0.07):
            # Create a list to hold pixel colors
            pixel_colors = [(0, 255, 0)] * self.led.count  # Initialize with off state

            for i in range(self.led.count):
                stripe_index = (i + offset) % stripe_cycle

                if stripe_index < size:
                    pixel_colors[i] = (255, 0, 0)  # Red
                elif stripe_index >= size + spacing and stripe_index < 2 * size + spacing:
                    pixel_colors[i] = (255, 255, 255)  # White

            # Batch update using tuple assignment
            for i, color in enumerate(pixel_colors):
                self.led.set_pixel(i, color)

            self.led.show()

            offset = (offset + 1) % stripe_cycle  # Increment and wrap the offset
