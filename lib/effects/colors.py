"""Color helpers for effects. Colors are 8-bit RGB tuples; float channel
and HSV parameters are 0.0-1.0 unless noted."""

import colorsys

from lib.drivers.base import Color


def to_rgb255(r: float, g: float, b: float) -> Color:
    """Convert 0.0-1.0 float channels to a clamped 0-255 int tuple."""
    return (
        max(0, min(255, int(r * 255))),
        max(0, min(255, int(g * 255))),
        max(0, min(255, int(b * 255))),
    )


def scale(color: Color, factor: float) -> Color:
    """Scale an RGB tuple by a 0.0-1.0 brightness factor."""
    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
    )


def lerp(a: Color, b: Color, t: float) -> Color:
    """Blend from `a` (t=0.0) to `b` (t=1.0)."""
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def hsv(h: float, s: float, v: float) -> Color:
    """HSV (all 0.0-1.0, hue wraps) to RGB."""
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return to_rgb255(r, g, b)


def adjust_hsv(
    color: Color, *, hue_shift: float = 0.0, saturation: float = 1.0
) -> Color:
    """Rotate a color's hue by `hue_shift` (0.0-1.0 = full circle) and
    multiply its saturation."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255.0 for c in color))
    h = (h + hue_shift) % 1.0
    s = max(0.0, min(1.0, s * saturation))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return to_rgb255(r, g, b)


def wheel(pos: float) -> Color:
    """Classic 256-step rainbow color wheel; `pos` wraps."""
    pos = int(pos) % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    pos -= 170
    return (0, pos * 3, 255 - pos * 3)


class Gradient:
    """Evenly spaced color stops sampled with linear interpolation.

    >>> heat = Gradient((0, 0, 0), (255, 0, 0), (255, 255, 0))
    >>> heat.sample(0.5)
    (255, 0, 0)
    """

    def __init__(self, *stops: Color):
        if len(stops) < 2:
            raise ValueError("Gradient needs at least two color stops")
        self.stops = stops

    def sample(self, t: float) -> Color:
        """Color at position `t` (0.0-1.0, clamped)."""
        segments = len(self.stops) - 1
        x = max(0.0, min(1.0, t)) * segments
        i = min(int(x), segments - 1)
        return lerp(self.stops[i], self.stops[i + 1], x - i)
