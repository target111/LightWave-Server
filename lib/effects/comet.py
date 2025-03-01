from lib.led import EffectBase

def calculate_intensity(color, intensity):
    return tuple(int(c * intensity) for c in color)

def colorwheel(pos):
    """Helper to create a rainbow color spectrum."""
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))

class RainbowComet(EffectBase):
    """
    A rainbow comet animation.

    :param speed: Animation speed in seconds, e.g. 0.1.
    :param tail_length: The length of the comet. Defaults to 25% of the length of the LED strip.
    :param reverse: Animates the comet in the reverse order. Defaults to False.
    :param bounce: Comet will bounce back and forth. Defaults to False.
    :param colorwheel_offset: Offset from start of colorwheel (0-255).
    :param step: Colorwheel step (defaults to automatic calculation).
    :param ring: Ring mode. Defaults to False.
    """

    def __init__(self, led, speed=0.01, tail_length=150, reverse=False, bounce=False, colorwheel_offset=0, step=0, ring=True):
        super().__init__(led)
        self.speed = speed
        self.tail_length = tail_length if tail_length else self.led.count // 4
        self.reverse = reverse
        self.bounce = bounce
        self.ring = ring

        if self.bounce and self.ring:
            raise ValueError("Cannot combine bounce and ring mode")

        self._color_step = 0.95 / self.tail_length
        self._comet_colors = None
        self._direction = -1 if self.reverse else 1
        self._left_side = -self.tail_length
        self._right_side = self.led.count
        self._tail_start = 0

        if self.ring:
            self._left_side = 0

        if step == 0:
            self._colorwheel_step = int(256 / self.tail_length)
        else:
            self._colorwheel_step = step
        self._colorwheel_offset = colorwheel_offset

        self.reset()

    def _set_color(self, color):
        # This method is now used to generate rainbow colors
        self._comet_colors = [(0, 0, 0)]  # Background color (black)
        for n in range(self.tail_length):
            invert = self.tail_length - n - 1
            self._comet_colors.append(
                calculate_intensity(
                    colorwheel(
                        int((invert * self._colorwheel_step) + self._colorwheel_offset)
                        % 256
                    ),
                    n * self._color_step + 0.05,
                )
            )

    def reset(self):
        """
        Resets to the first state.
        """
        if self.reverse:
            self._tail_start = self.led.count + self.tail_length + 1
        else:
            self._tail_start = -self.tail_length - 1

        if self.ring:
            self._tail_start = self._tail_start % self.led.count

    def _run(self):
        self._set_color(None)  # Generate rainbow colors (color argument is not used here)

        colors = self._comet_colors
        if self.reverse:
            colors = list(reversed(colors))

        start = self._tail_start
        npixels = self.led.count

        # Optimization: Fill with background color only in the area where the comet was previously
        if self.ring:
            self.led.set_pixel(start-self._direction, (0,0,0))
            if start == npixels:
                self.led.set_pixel(0, (0,0,0))
        else:
            if start-self._direction >= 0 and start-self._direction < npixels:
                self.led.set_pixel(start-self._direction, (0,0,0))
        
        if self.ring:
            start %= npixels
            for color in colors:
                self.led.set_pixel(start, color)
                start += 1
                if start == npixels:
                    start = 0
        else:
            for color in colors:
                if start >= npixels:
                    break
                if start >= 0:
                    self.led.set_pixel(start, color)
                start += 1

        self.led.show()

        self._tail_start += self._direction

        if self._tail_start < self._left_side or (
            self._tail_start >= self._right_side and not self.reverse
        ):
            if self.bounce:
                self.reverse = not self.reverse
                self._direction = -self._direction
            elif self.ring:
                self._tail_start = self._tail_start % self.led.count
            else:
                self.reset()

        self.stopped.wait(self.speed)
